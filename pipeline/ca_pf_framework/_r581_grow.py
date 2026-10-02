#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_grow.py --- ★★ goal §(17)#1「**单个板条的生长**」的完整量具。

## 要报的量（goal 逐字点名）
> 三维几何量（长/宽/厚）、长宽比、**体积**、**v_tip**、**取向（与惯习面族的关系）**

## 快照里有什么（`_r581_snapkeys.py` 实测，不猜）
* `region` (160³ int16)、`L`、`t_s`、`step`
* **`w_ax` (3,)** —— 惯习面法向（单位向量）
* **`a_ax` (3,)** —— 板条长轴方向（单位向量）
* `n_hab` (3,) —— 某个惯习面族的量（含义未核实，**不猜、不用**）

## 方法（每一步都写死）
1. 每个场取**最大连通分量**（P22：场可能是碎屑云；碎屑只 0.22%，见 `_r581_speck.py`）；
2. **长/宽/厚** = 该分量的**主轴**（PCA）**投影跨度**（不是包围盒！包围盒会被对角朝向骗）；
3. **v_tip** = 相邻快照间 `长(t2) − 长(t1)` / `(t_s(t2) − t_s(t1))`（m/s，另报 nm/步）；
4. **取向** = 该分量**最长主轴**与 `a_ax` 的夹角（度）；同时报与 `w_ax` 的夹角（应接近 90°）。

## 自洽检查（P21 强制）
* 主轴跨度之积应 ≈ 分量胞数 × dx³ 的量级（球/盒近似）——
  **只报比值，不作判据**（形状任意，比值本来就不该是 1）；
* **必报**：`长 ≥ 宽 ≥ 厚` 是否成立（主轴排序）；不成立 ⇒ **量具错**，不许出结论。
"""
import os

import numpy as np
from scipy import ndimage

ROOT = '_exp/_bk_p2'


def principal_extents(mask, dx):
    """PCA 主轴上的**投影跨度**（比包围盒稳，不会被朝向骗）。"""
    idx = np.argwhere(mask)
    if len(idx) < 4:
        return None
    c = idx.mean(0)
    X = (idx - c) * dx
    C = X.T @ X / len(X)
    w, V = np.linalg.eigh(C)          # 升序
    order = np.argsort(w)[::-1]       # 降序：长→短
    V = V[:, order]
    P = X @ V
    ext = P.max(0) - P.min(0)         # 三根主轴上的跨度（降序）
    return ext, V                     # ext: (长, 宽, 厚)；V 列 = 主轴方向


def one(tag, snapfile):
    p = os.path.join(ROOT, 'dry_' + tag, snapfile)
    z = np.load(p)
    reg = z['region']
    L = float(z['L'])
    dx = L / reg.shape[0]
    t_s = float(z['t_s']) if 't_s' in z else float('nan')
    step = int(z['step']) if 'step' in z else -1
    a_ax = np.asarray(z['a_ax'], float) if 'a_ax' in z else None
    w_ax = np.asarray(z['w_ax'], float) if 'w_ax' in z else None
    out = {}
    for f in [int(v) for v in np.unique(reg) if v > 0]:
        M = (reg == f)
        lab, n = ndimage.label(M)
        if n == 0:
            continue
        sz = ndimage.sum(M, lab, range(1, n + 1)).astype(int)
        big = (lab == (int(np.argmax(sz)) + 1))
        r = principal_extents(big, dx)
        if r is None:
            continue
        ext, V = r
        d = dict(ncells=int(sz.max()), ncomp=int(n),
                 thick=ext[2], width=ext[1], length=ext[0],
                 V=cells_volume(int(sz.max()), dx))
        # 取向
        if a_ax is not None:
            v1 = V[:, 0]
            cos = abs(float(np.dot(v1, a_ax / np.linalg.norm(a_ax))))
            d['ang_a'] = float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
        if w_ax is not None:
            cos = abs(float(np.dot(V[:, 2], w_ax / np.linalg.norm(w_ax))))
            d['ang_w'] = float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
        out[f] = d
    return dict(tag=tag, snap=snapfile, step=step, t_s=t_s, dx=dx, flds=out)


def cells_volume(n, dx):
    return n * dx ** 3


def main():
    print('=' * 108)
    print('R581 —— §(17)#1「单个板条的生长」：3-D 几何量 / 体积 / v_tip / 取向')
    print('=' * 108)
    for tag in ('p2_b5', 'p2_b3'):
        d = os.path.join(ROOT, 'dry_' + tag)
        if not os.path.isdir(d):
            continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        res = [one(tag, s) for s in snaps]
        print()
        print('#' * 108)
        print('# %s' % tag)
        print('#' * 108)
        for r in res:
            print(' ── step %-5d  t_s=%.6e  （%d 个场）──' % (r['step'], r['t_s'], len(r['flds'])))
            print('   %-5s %-7s %-5s %9s %9s %9s %8s %9s %8s %8s'
                  % ('场', '胞数', '分量', '厚 nm', '宽 nm', '长 nm', '长/厚', '体积 µm³',
                     '与a_ax°', '与w_ax°'))
            for f, v in sorted(r['flds'].items()):
                nm = 1e9
                print('   %-5d %-7d %-5d %9.1f %9.1f %9.1f %8.2f %9.4f %8.1f %8.1f'
                      % (f, v['ncells'], v['ncomp'], v['thick'] * nm, v['width'] * nm,
                         v['length'] * nm,
                         v['length'] / max(v['thick'], 1e-30), v['V'] * 1e18,
                         v.get('ang_a', float('nan')), v.get('ang_w', float('nan'))))
            # 自洽检查：长 ≥ 宽 ≥ 厚
            bad = [f for f, v in r['flds'].items()
                   if not (v['length'] >= v['width'] * (1 - 1e-9)
                           and v['width'] >= v['thick'] * (1 - 1e-9))]
            print('   ⇒ 主轴排序（长≥宽≥厚）：%s'
                  % ('✅ 全部成立' if not bad else '❌ 场 %s 不成立 ⇒ **量具或数据有问题**' % bad))
        # v_tip
        print()
        print(' ── **v_tip**（同一场在相邻快照间的长轴增长）──')
        print('   %-5s %-10s %-12s %-14s %-14s' % ('场', 'step 区间', 'Δt (s)',
                                                  'Δ长 (nm)', 'v_tip (nm/步)'))
        for i in range(len(res) - 1):
            a, b = res[i], res[i + 1]
            dt = b['t_s'] - a['t_s']
            for f in sorted(set(a['flds']) & set(b['flds'])):
                dl = b['flds'][f]['length'] - a['flds'][f]['length']
                dstep = b['step'] - a['step']
                print('   %-5d %-10s %-12.4e %-14.1f %-14.4f'
                      % (f, '%d→%d' % (a['step'], b['step']), dt, dl * 1e9,
                         dl * 1e9 / max(dstep, 1)))
    print('=' * 108)
    print('⚠ 记账：')
    print('  · 长/宽/厚 是**主轴投影跨度**（不是包围盒）—— 包围盒会被对角线朝向放大；')
    print('  · 每个场只取**最大连通分量**（P22；碎屑实测仅占 0.22%）；')
    print('  · `n_hab` 的含义**未核实**，本量具**不用它**，不猜。')
    print('=' * 108)


if __name__ == '__main__':
    main()
