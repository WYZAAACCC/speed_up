#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_a26.py --- ★★★ A26 结案：**同变体的板条是否共享同一个惯习面？**

## A26 是什么（R25 登记）
R25 实测：场 1 的厚度轴与 `w_ax` 差 **7.9°**，而场 2/3/4（`vmap_vals` **都 = 1**）
差 **89.4–89.8°** ⇒ 表面上看"**同变体却差 90°**" ⇒ 当时标【未核实】。

## 代码核实（`_bk_exp.py` 逐字，不猜）
* **L1292**：`vmap = {i + 1: laths_eff[i] for i in range(nv)}`
  ⇒ **`vmap_vals` 就是"场 → 变体号"** ✅（假设成立）
* **L546**：`_R0 = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[laths[0] - 1], float), _nref0)`
  ⇒ `a_ax = _R0[1]`、`w_ax = _R0[2]` 是**第 0 根板条（= 场 1）的变体**的（长轴、惯习面法向）
  ⇒ **`w_ax` 与场 1 同族 ⇒ 场 1 本该是 0° 附近**（实测 7.9° ✅ 自洽）

## 判据（**预先写死**）
* **H-A（轴指派伪影）**：场 1 的 **长/厚 只有 1.63**（两个小轴 578 vs 670 只差 16%）
  ⇒ 它的"厚度轴"**本来就不确定** ⇒ 7.9° 是**指派伪影**。
  ⇒ **可证伪的预测**：**把低长宽比的场排除后，同变体的场应当互相一致（差 ≪ 10°）**。
* **H-B（真的取向不同）**：同变体但取向真的差 90° ⇒ **物理错**。

## 怎么判
**逐场两两比"厚度轴夹角"**，按 `vmap_vals`（变体）分组：
* 同变体组内夹角 **小（≪10°）** ⇒ **H-A**（物理对，场 1 是伪影）
* 同变体组内夹角 **≈90°** ⇒ **H-B**（物理错，要报警）
**并且**：对**长/厚 < 2** 的场单独标出（它们不该参与取向统计）。
"""
import os

import numpy as np
from scipy import ndimage

ROOT = '_exp/_bk_p2'


def axes_of(mask, dx):
    idx = np.argwhere(mask)
    c = idx.mean(0)
    X = (idx - c) * dx
    C = X.T @ X / len(X)
    w, V = np.linalg.eigh(C)
    o = np.argsort(w)[::-1]
    V = V[:, o]
    P = X @ V
    ext = P.max(0) - P.min(0)
    return ext, V


def main():
    print('=' * 100)
    print('R581 —— A26 结案：同变体的板条共享惯习面吗？')
    print('=' * 100)
    for tag in ('p2_b5', 'p2_b3'):
        d = os.path.join(ROOT, 'dry_' + tag)
        if not os.path.isdir(d):
            continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        z = np.load(os.path.join(d, snaps[-1]))
        reg = z['region']
        L = float(z['L']); dx = L / reg.shape[0]
        vk = np.asarray(z['vmap_keys']).ravel()
        vv = np.asarray(z['vmap_vals']).ravel()
        vm = {int(a): int(b) for a, b in zip(vk, vv)}
        w_ax = np.asarray(z['w_ax'], float); w_ax /= np.linalg.norm(w_ax)
        print()
        print('#' * 100)
        print('# %s  （末快照 %s）  `w_ax`（参考惯习法向）= %s'
              % (tag, snaps[-1], np.round(w_ax, 5)))
        print('#' * 100)
        rec = {}
        for f in [int(v) for v in np.unique(reg) if v > 0]:
            M = (reg == f)
            lab, n = ndimage.label(M)
            sz = ndimage.sum(M, lab, range(1, n + 1)).astype(int)
            big = (lab == (int(np.argmax(sz)) + 1))
            ext, V = axes_of(big, dx)
            t_ax = V[:, 2]                       # 厚度轴
            cos = abs(float(np.dot(t_ax, w_ax)))
            ang = float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
            rec[f] = dict(var=vm.get(f, -1), ext=ext, t_ax=t_ax, ang=ang,
                          AR=float(ext[0] / max(ext[2], 1e-30)))
        print('   %-5s %-6s %-9s %-9s %s' % ('场', '变体', '长/厚', '厚轴与w°', '备注'))
        for f, v in sorted(rec.items()):
            note = ''
            if v['AR'] < 2.0:
                note = '⚠ **长/厚<2 ⇒ 厚度轴指派不确定，不参与取向统计**'
            print('   %-5d %-6d %-9.2f %-9.1f %s' % (f, v['var'], v['AR'], v['ang'], note))
        print()
        print('   ── **同变体组内**的厚度轴两两夹角（**只算长/厚 ≥ 2 的场**）──')
        good = [f for f, v in rec.items() if v['AR'] >= 2.0]
        byvar = {}
        for f in good:
            byvar.setdefault(rec[f]['var'], []).append(f)
        ok = True
        for var, fs in sorted(byvar.items()):
            if len(fs) < 2:
                print('     变体 %-3d：只有 1 个场（%s）⇒ 无可比' % (var, fs)); continue
            print('     变体 %-3d：场 %s' % (var, fs))
            for i in range(len(fs)):
                for j in range(i + 1, len(fs)):
                    c = abs(float(np.dot(rec[fs[i]]['t_ax'], rec[fs[j]]['t_ax'])))
                    a = float(np.degrees(np.arccos(np.clip(c, -1, 1))))
                    a = min(a, 180 - a)
                    good_pair = (a < 10)
                    ok &= good_pair
                    print('       场 %-3d–%-3d 夹角 **%6.2f°**  %s'
                          % (fs[i], fs[j], a, '✅ 一致' if good_pair else '❌ **差 90° ⇒ H-B**'))
        print()
        print('   ⇒ 判据（**预先写死**）：同变体组内夹角 ≪10° ⇒ **H-A**（物理对）；≈90° ⇒ **H-B**（物理错）')
        print('   ⇒ 本臂判定：**%s**' % ('H-A（物理对，场 1 是轴指派伪影）' if ok else 'H-B（物理错！）'))
    print('=' * 100)
    print('⚠ 记账：`vmap_vals` = 变体号（`_bk_exp.py:1292` 逐字）；')
    print('  `w_ax`/`a_ax` = **第 0 根板条（场 1）**那个变体的轴（`:546`）。')
    print('  长/厚 < 2 的场（本仓的场 1）厚度轴指派不确定 ⇒ **必须排除出取向统计**。')
    print('=' * 100)


if __name__ == '__main__':
    main()
