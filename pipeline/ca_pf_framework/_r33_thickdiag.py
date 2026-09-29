#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r33_thickdiag.py —— 诊断 **P1-20**：块沿 n* 的跨度为什么长得比 β_h 预言快 ~95 倍？

## 问题
`mb1s`（`--beta-h 6.477`、Δx=125 nm）实测场 1 的 n* 跨度 635 → 2528 nm（1500 步），
即 ~2.8 nm/步；而 `β_h` 预言 `0.15·Δx·e^{−β_h} = 0.029 nm/步` ⇒ **差 ≈95×**。

## 三个互斥候选（本脚本用**落盘的带内稀疏 φ**把它们分开，不需要新仿真）
* **H-A「宽面真的在推进」** ⇒ 宽面（`|n·n*| > 0.9` 的界面胞）的 n* 位置应移动 ~2.8 nm/步。
* **H-B「端面/侧面在长」** ⇒ 宽面几乎不动（≤ β_h 预言），而**斜法向**界面胞的 n*
  位置大范围铺开；n* 跨度是被**边缘**撑大的 ⇒ 那是**量具口径**问题，不是物理。
* **H-C「碎片/孤儿污染」** ⇒ 统计里混进了与主板条无关的孤岛。

## 做法（口径先写死）
1. 由 `band_idx/band_val/band_fld` 重建 φ（带外 NaN）。
2. 取**可信内层** `|φ| ≤ (band_cells−2)·Δx` 算 `∇φ`（R30 已实测：该内层逐位可复算）。
3. 界面胞 = `|φ| ≤ 1.5Δx`；法向 `n = ∇φ/|∇φ|`。
4. 按 `|n·n*|` 分三档：**宽面** >0.9、**斜** 0.3–0.9、**端/侧** <0.3。
5. 每档报沿 n* 的**位置分位**（p05/中位/p95）与胞数。
   ⇒ H-A：宽面档的中位随步移动；H-B：宽面档不动而端/侧档的 p05/p95 外扩。

用法：  python3 _r33_thickdiag.py _exp/_bk_mb/dry_mb1s [--field 1]
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
    want = int(sys.argv[sys.argv.index('--field') + 1]) if '--field' in sys.argv else 1
    snaps = [s for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
             if 'band_idx' in np.load(s).files]
    if not snaps:
        raise SystemExit('✗ 该目录没有带 band_* 的快照')
    print('目录 %s；%d 个带 φ 的快照；被诊断的场 = %d' % (d, len(snaps), want))
    z0 = np.load(snaps[0])
    n_hab = np.asarray(z0['n_hab'], float)
    n_hab = n_hab / np.linalg.norm(n_hab)
    print('  n* = %s' % np.array2string(n_hab, precision=4))
    print('  %-6s %-4s %-9s | %-26s | %-26s | %s'
          % ('step', 'N', 'band_cells', '宽面 |n·n*|>0.9（nm）',
             '斜 0.3–0.9（nm）', '端/侧 <0.3（nm）'))
    for s in snaps:
        z = np.load(s)
        N = int(z['N'])
        dx = float(z['L']) / N
        bc = int(z['band_cells'])
        nreg = len(z['vmap_keys']) + 1
        phi = load_phi(z, nreg, N)
        p = phi[want]
        if not np.isfinite(p).any():
            print('  %-6d （场 %d 无带内 φ）' % (int(z['step']), want))
            continue
        pf = np.where(np.isfinite(p), p, 1e3)          # 带外填大值 ⇒ 不参与
        inner = np.abs(pf) <= (bc - 2) * dx
        g = np.gradient(pf, dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
        prj = (n_hab[0] * (np.arange(N) * dx)[:, None, None]
               + n_hab[1] * (np.arange(N) * dx)[None, :, None]
               + n_hab[2] * (np.arange(N) * dx)[None, None, :])
        iface = inner & (np.abs(pf) <= 1.5 * dx)
        c2 = np.clip(sum(g[i] / gn * n_hab[i] for i in range(3)) ** 2, 0.0, 1.0)
        out = []
        for lo, hi in ((0.81, 1.01), (0.09, 0.81), (-0.01, 0.09)):
            m = iface & (c2 >= lo) & (c2 < hi)
            if m.sum() < 20:
                out.append('%-24s' % ('n=%d（太少）' % int(m.sum())))
                continue
            v = prj[m] * 1e9
            out.append('p05/med/p95=%6.0f/%6.0f/%6.0f' % (
                np.percentile(v, 5), np.median(v), np.percentile(v, 95)))
        # 板条**沿 n\* 的实心跨度**（只看这个场自己的胞，而不是全块）
        own = (z['region'] == want)
        span = (np.ptp(prj[own]) * 1e9) if own.any() else float('nan')
        print('  %-6d %-4d %-9d | %-26s | %-26s | %s   ‖本场 n*跨度=%.0f nm'
              % (int(z['step']), N, bc, out[0], out[1], out[2], span))


if __name__ == '__main__':
    main()
