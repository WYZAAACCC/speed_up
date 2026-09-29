#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT ★★：**`region` 口径 vs `phi` 口径的界面位置差**（量化地板）。

这是"落盘够不够重算"的**判决性实验**（只读，不改已有文件）：

* CSV/`snap` 里的 `f3_pos` 全部是 **`region` 口径**（`_bk_measure.py:408-415`：
  F3 胞的 `n*·x` **角点坐标**均值）。
* 真实界面位置是 @@\\varphi=0@@ 的**亚胞**位置 —— 那**只能从 `phi` 读**。
* ⇒ 取**同时存了 `region` 与 `phi`** 的快照（`_bk_block/*`、`_bk_f3smoke/*`），
  用两种口径各算一次界面位置，差值就是 **`region` 口径的量化误差**。

⚠ 这里 F3 是两个场之间的界面，取它们的 φ 差 `phi_i − phi_j`；
  只有**两个场都活跃**的界面才有定义。
用法: python3 _r30_posfloor.py <dir-or-npz> ...
"""
import glob
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _bk_measure as BM                                          # noqa: E402


def diff_on_centers(a, dx):
    """三轴中心差分（周期），返回逐轴梯度（与 `np.gradient(edge_order=1)` 等价）。"""
    g = np.empty((3,) + a.shape, np.float64)
    for ax in range(3):
        g[ax] = (np.roll(a, -1, axis=ax) - np.roll(a, 1, axis=ax)) / (2 * dx)
    return g


def main(paths):
    print('%-46s %8s %12s %12s %12s' % ('snap', 'nf3cell', 'pos_reg[m]',
                                        'pos_phi[m]', 'Δpos[m]'))
    rows = []
    for p in paths:
        z = np.load(p, allow_pickle=False)
        if 'phi' not in z.files or 'region' not in z.files:
            z.close()
            continue
        reg = z['region']
        phi = z['phi']
        N = reg.shape[0]
        dx = float(z['L']) / N
        n_hab = np.asarray(z['n_hab'], float)
        # ⚠ `_bk_smoke_f3.py:225` 只存 `nv`，**不存 `vmap`** ⇒ 快照里没有
        #   "哪个场属于哪个变体"（`vmap` 只在 `meta.json` 里）⇒ 只能退化成
        #   "全部场同一变体"（与 `_bk_measure.py:673-675` 的 fallback 一致）。
        if 'vmap_keys' in z.files:
            vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'],
                                                   z['vmap_vals'])}
        else:
            nv = int(z['nv']) if 'nv' in z.files else int(reg.max())
            vmap = {k: 1 for k in range(1, nv + 1)}
        # ---- region 口径：F3 胞的角点坐标均值（`_bk_measure.py:408-415`）----
        mm = BM.measure_state(reg, dx, n_hab, z['w_ax'], z['a_ax'], vmap)
        pos_reg = mm['f3_pos_n']
        # ---- 重建 f3_cells（与 `_bk_measure.py:390-403` 逐字同构）----
        laths = sorted(vmap)
        f3 = np.zeros(reg.shape, bool)
        for i, ki in enumerate(laths):
            for kj in laths[i + 1:]:
                if vmap[ki] != vmap[kj]:
                    continue
                mi, mj = (reg == ki), (reg == kj)
                if not mi.any() or not mj.any():
                    continue
                for ax in (0, 1, 2):
                    for sh in (1, -1):
                        t = mi & np.roll(mj, sh, axis=ax)
                        f3 |= t
                        f3 |= (mj & np.roll(mi, sh, axis=ax))
        # ---- phi 口径：在 F3 胞上取 grad(phi_i − phi_j)·n*/|grad| ，求零点偏移 ----
        gc = BM._bbox_of(f3) if f3.any() else None
        if gc is None:
            z.close()
            continue
        ii = np.arange(N)
        cc = [ii[gc[0].start:gc[0].stop] * dx,
              ii[gc[1].start:gc[1].stop] * dx,
              ii[gc[2].start:gc[2].stop] * dx]
        pn = (n_hab[0] * cc[0][:, None, None] + n_hab[1] * cc[1][None, :, None]
              + n_hab[2] * cc[2][None, None, :])
        sub = f3[gc]
        vals = []
        for i, ki in enumerate(laths):
            for kj in laths[i + 1:]:
                if vmap[ki] != vmap[kj]:
                    continue
                d = (phi[ki] - phi[kj]).astype(np.float64)
                g = diff_on_centers(d, dx)
                gn = np.sqrt((g ** 2).sum(0)) + 1e-30
                dn = (g[0] * n_hab[0] + g[1] * n_hab[1] + g[2] * n_hab[2]) / gn
                # 亚胞零点：x0 = x − d/ (∂d/∂n)，逐胞
                off = -d / np.where(np.abs(dn) > 1e-3, dn, np.nan)
                off_sub = off[gc]
                sub_reg = reg[gc]
                m = sub & np.isfinite(off_sub) & (np.abs(off_sub) < 2 * dx) \
                    & ((sub_reg == ki) | (sub_reg == kj))
                if m.sum() == 0:
                    continue
                vals.append(float(np.nanmean((pn + off_sub)[m])))
        pos_phi = float(np.mean(vals)) if vals else float('nan')
        dpos = (pos_reg - pos_phi) if np.isfinite(pos_phi) else float('nan')
        print('%-46s %8d %12.6g %12.6g %12.6g'
              % (p.replace('/mnt/f/speed_up/pipeline/ca_pf_framework/', ''),
                 int(f3.sum()), pos_reg, pos_phi, dpos))
        if np.isfinite(dpos):
            rows.append((abs(dpos) / dx, dpos, p, dx))
        z.close()
    print()
    if rows:
        rows.sort(reverse=True)
        print('=== |Δpos| 最大的 8 个（单位：Δx）===')
        for r in rows[:8]:
            print('   |Δ|=%.4f Δx  (Δ=%.4g m, dx=%.4g m)  %s'
                  % (r[0], r[1], r[3], r[2]))
        a = np.array([r[0] for r in rows])
        print('   n=%d  中位 %.4f Δx  max %.4f Δx  ⇒ **V-3g 门槛是 0.12 Δx**'
              % (a.size, float(np.median(a)), float(a.max())))
        print('   dx=%s' % rows[0][3])
    return 0


if __name__ == '__main__':
    ps = []
    for a in sys.argv[1:]:
        ps += sorted(glob.glob(os.path.join(a, 'snap_*.npz'))) \
            if os.path.isdir(a) else [a]
    sys.exit(main(ps))
