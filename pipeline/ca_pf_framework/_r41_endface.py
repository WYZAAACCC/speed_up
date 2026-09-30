#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r41_endface.py —— **端面推进速率**：核心长大 0.7 nm/步 的机理诊断。

## 为什么（P1-24 的遗留问题）
MB-1 实测：核心沿长轴 `a` 的跨度 1500 步只长 **+1104 nm ⇒ ≈0.7 nm/步**。
但按迁移率算，**端面**（法向 ≈ ±a）的钉扎因子是
`M(a)/M0 = exp(−β_h·(a·n*)²) = exp(−6.477 × 0.127²) = 0.901`
⇒ 端面本该以 `0.15Δx × 0.901 = 16.9 nm/步` 推进 —— **比实测快 24 倍**。

⇒ 三种可能，本脚本用**落盘的带内稀疏 φ** 把它们分开：
* **H-α「端面确实推得快，但板的实际长轴在转」** ⇒ 端面位置沿 `a` 快速移动，
  而"沿 a 的跨度"因转动而长得慢。
* **H-β「端面被别的机制挡住」**（弹性回应力 / 曲率）⇒ 端面位置基本不动。
* **H-γ「端面根本不存在」**（种子是长条，但长大后台面变圆）⇒
  满足 `(n·a)² > 0.81` 的界面胞**很少**。

## 口径（先写死）
对每个场：界面胞 = `|φ| ≤ 1.5Δx`；法向 `n = ∇φ/|∇φ|`；
**端面胞** = `(n·a)² > 0.81`；以该场质心分 ±两簇，报两簇沿 `a` 的中位位置与**端面胞数**。

用法：  python3 _r41_endface.py _exp/_bk_mb/dry_mb1s --field 1
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from _r33_thickdiag import load_phi                             # noqa: E402
from _r33_remeasure import variant_axes                         # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = sys.argv[1]
    k = int(sys.argv[sys.argv.index('--field') + 1]) if '--field' in sys.argv else 1
    # ★ R46：`--axis {a,w,n}` —— 量哪一对面的位置（默认 a = 尖端）。
    #   动机：`a` 方向的"跨度增长"已被**端面位置**独立验证过（只有 +577 nm），
    #   而 `w` 方向的 4× 跨度增长**还没有**同样的验证 ⇒ 用同一把尺子量 `w`。
    ax_name = sys.argv[sys.argv.index('--axis') + 1] if '--axis' in sys.argv else 'a'
    snaps = [s for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
             if 'band_idx' in np.load(s).files]
    if not snaps:
        raise SystemExit('✗ 没有带 band_* 的快照')
    z0 = np.load(snaps[0])
    vm = {int(a): int(b) for a, b in zip(z0['vmap_keys'], z0['vmap_vals'])}
    v = vm.get(k)
    if v is None:
        raise SystemExit('✗ 场 %d 不在 vmap 里' % k)
    n_ax, a_ax, w_ax = variant_axes(v)
    _AX = {'a': a_ax, 'w': w_ax, 'n': n_ax}[ax_name]
    print('目录 %s；场 %d（变体 V%d）；**被测轴 = %s** = %s'
          % (d, k, v, ax_name, np.array2string(_AX, precision=4)))
    print('  该轴法向的钉扎因子 M/M0 = exp(−β_h·(u·n*)²−β_w·(u·w)²) = **%.4f**'
          % float(np.exp(-6.477 * float(_AX @ n_ax) ** 2
                         - 2.3 * float(_AX @ w_ax) ** 2)))
    print('  %-6s %-8s %-13s %-13s %-11s %s'
          % ('step', '该面胞数', '−面位置 nm', '+面位置 nm', '两面间距', '沿该轴跨度'))
    for s in snaps:
        z = np.load(s)
        N = int(z['N'])
        dx = float(z['L']) / N
        bc = int(z['band_cells'])
        nreg = len(z['vmap_keys']) + 1
        phi = load_phi(z, nreg, N)
        p = phi[k]
        if not np.isfinite(p).any():
            continue
        pf = np.where(np.isfinite(p), p, 1e3)
        inner = np.abs(pf) <= (bc - 2) * dx
        g = np.gradient(pf, dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
        ca2 = np.clip(sum(g[i] / gn * _AX[i] for i in range(3)) ** 2, 0.0, 1.0)
        ef = inner & (np.abs(pf) <= 1.5 * dx) & (ca2 > 0.81)
        ii = np.arange(N) * dx
        pu = (_AX[0] * ii[:, None, None] + _AX[1] * ii[None, :, None]
              + _AX[2] * ii[None, None, :])
        own = (z['region'] == k)
        span = float(np.ptp(pu[own])) * 1e9 if own.any() else float('nan')
        if int(ef.sum()) < 20:
            print('  %-6d %-8d %-13s %-13s %-11s %.0f'
                  % (int(z['step']), int(ef.sum()), '（太少）', '—', '—', span))
            continue
        vv = pu[ef] * 1e9
        c = float(np.median(pu[own])) * 1e9
        lo, hi = vv[vv < c], vv[vv >= c]
        if lo.size < 10 or hi.size < 10:
            print('  %-6d %-8d %-13s %-13s %-11s %.0f'
                  % (int(z['step']), int(ef.sum()), '（两簇不均）', '—', '—', span))
            continue
        ml, mh = float(np.median(lo)), float(np.median(hi))
        print('  %-6d %-8d %-13.0f %-13.0f %-11.0f %.0f'
              % (int(z['step']), int(ef.sum()), ml, mh, mh - ml, span))


if __name__ == '__main__':
    main()
