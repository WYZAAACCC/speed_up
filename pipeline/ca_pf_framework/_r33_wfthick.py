#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r33_wfthick.py —— **宽面厚度**：P1-20 的直接产物（`V-8b` 的口径收窄）。

## 为什么需要它（`R30_AUDIT_LEDGER.md` P1-20 的实测）
`V-8b` 与 `C-5` 用的 `ths`（= `_bk_measure` 的 `n_%d`，即板条胞沿 n* 的**包围盒跨度**）
会把「**某一侧的迁移**」与「**端/侧面长大**」读成「**板条增厚**」：
实测 `mb1s` 场 1 —— 宽面**一侧** 1500 步只动 **26 nm**（0.017 nm/步 ≈ β_h 预言），
而包围盒跨度涨了 **+2007 nm**。

## 本工具的口径（先写死）
对每个场 `k`：
1. 由落盘的 `band_*` 重建 φ，取**可信内层** `|φ| ≤ (band_cells−2)Δx`；
2. 界面胞 = `|φ| ≤ 1.5Δx`，法向 `n = ∇φ/|∇φ|`；
3. **宽面胞** = `|n·n*| > 0.9`；
4. 以该场胞的 n* 质心为界，把宽面胞分成 **±两簇**；
5. `t_wf` = **两簇各自中位位置之差**（即"两张宽面之间的距离" = 板条厚度）；
6. 同时报两簇各自的**中位位置绝对值**（判"是否一侧在动"）。

⇒ 对"端面/侧面长大"**免疫**（那些胞的 `|n·n*|` 小，进不了第 3 步）。

用法：  python3 _r33_wfthick.py _exp/_bk_mb/dry_mb1s --fields 1,2,3
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402


def load_phi(z, nreg, N):
    phi = np.full((nreg, N, N, N), np.nan)
    idx = z['band_idx'].astype(np.int64)
    val = z['band_val'].astype(np.float64)
    fld = z['band_fld'].astype(np.int64)
    for k in range(nreg):
        s = (fld == k)
        if s.any():
            phi[k].ravel()[idx[s]] = val[s]
    return phi


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = sys.argv[1]
    fields = [1, 2, 3]
    if '--fields' in sys.argv:
        fields = [int(x) for x in sys.argv[sys.argv.index('--fields') + 1].split(',')]
    snaps = [s for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
             if 'band_idx' in np.load(s).files]
    if not snaps:
        raise SystemExit('✗ 没有带 band_* 的快照')
    z0 = np.load(snaps[0])
    n_hab = np.asarray(z0['n_hab'], float)
    n_hab = n_hab / np.linalg.norm(n_hab)
    print('目录 %s；%d 个带 φ 的快照；n* = %s'
          % (d, len(snaps), np.array2string(n_hab, precision=4)))
    print('  %-6s %-5s %-11s %-11s %-11s %s'
          % ('step', 'field', '包围跨度 nm', '**宽面厚 t_wf**', '两宽面中位 nm',
             '宽面胞数'))
    for s in snaps:
        z = np.load(s)
        N = int(z['N'])
        dx = float(z['L']) / N
        bc = int(z['band_cells'])
        nreg = len(z['vmap_keys']) + 1
        phi = load_phi(z, nreg, N)
        reg = z['region']
        ii = np.arange(N) * dx
        prj = (n_hab[0] * ii[:, None, None] + n_hab[1] * ii[None, :, None]
               + n_hab[2] * ii[None, None, :])
        for k in fields:
            if k >= nreg:
                continue
            own = (reg == k)
            if not own.any():
                continue
            bb = np.ptp(prj[own]) * 1e9
            p = phi[k]
            if not np.isfinite(p).any():
                print('  %-6d %-5d %-11.0f %-11s %-11s %s'
                      % (int(z['step']), k, bb, '（无 φ）', '—', '—'))
                continue
            pf = np.where(np.isfinite(p), p, 1e3)
            inner = np.abs(pf) <= (bc - 2) * dx
            g = np.gradient(pf, dx, edge_order=2)
            gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
            c2 = np.clip(sum(g[i] / gn * n_hab[i] for i in range(3)) ** 2, 0.0, 1.0)
            wf = inner & (np.abs(pf) <= 1.5 * dx) & (c2 > 0.81)
            if int(wf.sum()) < 20:
                print('  %-6d %-5d %-11.0f %-11s %-11s %d（太少）'
                      % (int(z['step']), k, bb, 'n/a', '—', int(wf.sum())))
                continue
            v = prj[wf] * 1e9
            c = float(np.median(prj[own]) * 1e9)
            lo, hi = v[v < c], v[v >= c]
            if lo.size < 10 or hi.size < 10:
                print('  %-6d %-5d %-11.0f %-11s %-11s %d（两簇不均）'
                      % (int(z['step']), k, bb, 'n/a', '—', int(wf.sum())))
                continue
            t_wf = float(np.median(hi) - np.median(lo))
            print('  %-6d %-5d %-11.0f %-11.1f %-11s %d'
                  % (int(z['step']), k, bb, t_wf,
                     '%.0f / %.0f' % (np.median(lo), np.median(hi)), int(wf.sum())))


if __name__ == '__main__':
    main()
