#!/usr/bin/env python3
"""R65: **直测棱角圆化** —— 把"棱角被磨圆到 ~Δx"从推断变成实测。

## 动机（`R30_AUDIT_LEDGER.md` §55）
两级传递率：设计 `M` 比 8.98 → **面速度比 5.95（66%）** → **形状比 1.6（27%）**。
损失主要在第二级 ⇒ 猜想"形状的极端位置由**被磨圆的棱角**决定"。
本脚本**直接量这件事**。

## 口径（先写死）
从落盘的**带内稀疏 φ**（`band_idx/val/fld`）取场 1 的界面点云（`|φ| ≤ 0.5Δx`），
法向 `n = ∇φ/|∇φ|`（`np.gradient`，`edge_order=2`）。

* **`f_tip`** = 在"沿 `a` 最靠前的 10% 界面点"里，法向与 `a` 夹角 **≤25°** 的比例。
  * **尖棱柱**（理想）⇒ `f_tip → 1`；
  * **半球端**（完全磨圆）⇒ `f_tip` 很小（只有一点法向恰好沿 `a`）。
* **`f_flat`** = 全体界面点里 `|n·a| > cos25°` 的比例（tip 面族的面积占比）。
  * 解析长方体应 ≈ 端面面积/总面积。
"""
import glob
import os
import sys

import numpy as np

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_single'
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
print('臂 %s  快照 %d 个' % (D, len(snaps)))
print()
print('  %-6s %-9s %-9s %-9s %-9s %s'
      % ('step', 'f_tip', 'f_flat', 'a 跨度', 'w 跨度', 'tip 点数'))
rec = []
for s in snaps:
    z = np.load(s)
    if 'band_idx' not in z.files:
        continue
    N = int(z['N'])
    dx = float(z['L']) / N
    aa = np.asarray(z['a_ax'], float)
    ww = np.asarray(z['w_ax'], float)
    fld = z['band_fld']
    sel = (fld == 1)
    if not sel.any():
        continue
    idx, val = z['band_idx'][sel], z['band_val'][sel]
    phi = np.full(N ** 3, np.nan, np.float32)
    phi[idx] = val
    phi = phi.reshape(N, N, N)
    if not np.isfinite(phi).any():
        continue
    pf = np.where(np.isfinite(phi), phi, 1e3)
    g = np.gradient(pf, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    nrm = np.stack([x / gn for x in g], -1)
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    P = np.stack([X, Y, Z], -1)
    m = np.isfinite(phi) & (np.abs(phi) <= 0.5 * dx)
    if int(m.sum()) < 50:
        continue
    pts, nv = P[m], nrm[m]
    pa = pts @ aa
    c2 = np.clip(nv @ aa, -1, 1) ** 2
    thr = np.quantile(pa, 0.90)
    tip = pa >= thr
    f_tip = float((c2[tip] > np.cos(np.radians(25)) ** 2).mean())
    f_flat = float((c2 > np.cos(np.radians(25)) ** 2).mean())
    rec.append((int(z['step']), f_tip, f_flat, len(pts)))
    pw = pts @ ww
    print('  %-6d %-9.3f %-9.3f %-9.0f %-9.0f %d'
          % (z['step'], f_tip, f_flat,
             (pa.max() - pa.min()) * 1e9, (pw.max() - pw.min()) * 1e9,
             int(tip.sum())))
if rec:
    print()
    print('=== 判读')
    print('  `f_tip` = 最靠前 10% 界面点里、法向在 **a 的 25° 内** 的比例：')
    print('    尖棱柱 ⇒ →1；半球端 ⇒ 很小。')
    print('  首末 f_tip: %.3f → %.3f' % (rec[0][1], rec[-1][1]))
    print('  首末 f_flat: %.3f → %.3f' % (rec[0][2], rec[-1][2]))
    print()
    print('  ★ 若 `f_tip` 从 ~1 掉到 ≪1 ⇒ **棱角确实被磨圆**（§55 的猜想成立），')
    print('    则"形状各向异性塌"有直接的几何证据，下一步做"保住棱角"。')
