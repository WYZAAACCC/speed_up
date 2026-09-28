#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_proj.py --- D17 探针：`proj` 格式在周期斜面算例上"中位精确、少数胞爆掉"的定位。

只做一件事：把一步 `advance` 内部的**每个中间量**都量出来，找出爆掉的位置与来源。
（`MEASUREMENT_SPEC.md` R0/R3：先量，不要先推理。）
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T19_verify_proj import plane_setup, _wrap_field            # noqa: E402

DF, MOB = 2.0e8, 1e-9
EXACT = MOB * DF

N, dx = 100, 30e-9
L = N * dx
n_h = np.array([1.0, 2.0, 3.0]) / np.sqrt(14.0)

for adv in ('central', 'proj'):
    g, d0 = plane_setup(N, dx, n_h, L)
    dt = 0.15 * dx / EXACT
    reg0 = g.region()
    print('=' * 100)
    print('adv=%s  N=%d dx=%.1f nm  nreg=%d  |V| 期望 = M·DF = %.4g'
          % (adv, N, dx * 1e9, g.nreg, EXACT))
    # ---- 一步之前：手工复算内部量 ----
    ph = g.phi
    karr = np.argmin(ph, axis=0)
    larr = np.empty(karr.shape, dtype=karr.dtype)
    _best = np.full(karr.shape, np.inf)
    for j in range(g.nreg):
        m = (karr != j) & (ph[j] < _best)
        larr[m] = j
        _best[m] = ph[j][m]
    pha = np.take_along_axis(ph, karr[None], 0)[0]
    phb = np.take_along_axis(ph, larr[None], 0)[0]
    sigma = np.where(karr < larr, 1.0, -1.0)
    d = sigma * (pha - phb)
    gd = np.gradient(d, dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
    print('  d = sigma(pha−phb):  min=%.4g max=%.4g' % (d.min(), d.max()))
    print('  |∇d| 分位 p1/p50/p99/max = %.4f / %.4f / %.4f / %.4g'
          % tuple(np.percentile(gn, [1, 50, 99]).tolist() + [gn.max()]))
    # 界面胞：|phiw| <= 2dx
    phiw = np.min(ph, axis=0)
    iface = np.abs(phiw) <= 2.0 * dx
    print('  iface 胞数 = %d ; |phiw| 的分位（iface 内）p50/p99/max = %.4g / %.4g / %.4g'
          % (iface.sum(),
             *np.percentile(np.abs(phiw)[iface], [50, 99]).tolist(), np.abs(phiw)[iface].max()))
    # 大梯度在哪？(|∇d| 大的胞，看它们离界面多远)
    big = gn > 5.0
    print('  |∇d|>5 的胞数 = %d (%.4f%%) ; 这些胞中 |phiw|<=2dx 的比例 = %.4f'
          % (big.sum(), 100.0 * big.mean(),
             float((np.abs(phiw)[big] <= 2 * dx).mean()) if big.any() else np.nan))
    if big.any():
        pos = np.argwhere(big)
        print('     它们的位置范围 x∈[%d,%d] y∈[%d,%d] z∈[%d,%d]（盒 %d）'
              % (pos[:, 0].min(), pos[:, 0].max(), pos[:, 1].min(), pos[:, 1].max(),
                 pos[:, 2].min(), pos[:, 2].max(), N))
        print('     其中 |∇d| p50/p99/max = %.3g / %.3g / %.3g'
              % tuple(np.percentile(gn[big], [50, 99]).tolist() + [gn[big].max()]))
    # 界面胞集合里 |∇d| 是否正常（应 = 2）
    print('  iface 内 |∇d| p1/p50/p99 = %.4f / %.4f / %.4f'
          % tuple(np.percentile(gn[iface], [1, 50, 99]).tolist()))
    # ---- 推进 20 步后看残差空间分布 ----
    for it in range(20):
        g.advance(dt, band_cells=20, adv_grad=adv)
    t = 20 * dt
    phi_ex = d0 - EXACT * t
    bm = np.abs(phi_ex) <= 3.0 * dx
    resid = g.phi[1] - phi_ex
    rb = np.abs(resid)[bm] / dx
    print('  20 步后：bm 胞数=%d  |resid|/dx p50/p90/p99/max = %.3g / %.3g / %.3g / %.3g'
          % (bm.sum(), *np.percentile(rb, [50, 90, 99]).tolist(), rb.max()))
    bad = bm & (np.abs(resid) > 3 * dx)
    print('  |resid|>3dx 的胞数 = %d（占 bm 的 %.4f%%）' % (bad.sum(), 100.0 * bad.sum() / bm.sum()))
    if bad.any():
        pos = np.argwhere(bad)
        print('     位置 x∈[%d,%d] y∈[%d,%d] z∈[%d,%d]' %
              (pos[:, 0].min(), pos[:, 0].max(), pos[:, 1].min(), pos[:, 1].max(),
               pos[:, 2].min(), pos[:, 2].max()))
        print('     该处 φ_1 当前值 p50=%.4g  φ_ex p50=%.4g  |∇φ_1| p50=%.4g'
              % (np.median(g.phi[1][bad]), np.median(phi_ex[bad]),
                 np.median(np.sqrt(sum(t2 ** 2 for t2 in np.gradient(g.phi[1], dx)))[bad])))
    print('  φ_1 的 |∇φ| 全局 p50/p99/max = %.4f / %.4f / %.4g'
          % tuple(np.percentile(np.sqrt(sum(t2 ** 2 for t2 in np.gradient(g.phi[1], dx))),
                                [50, 99]).tolist()
                  + [np.sqrt(sum(t2 ** 2 for t2 in np.gradient(g.phi[1], dx))).max()]))
