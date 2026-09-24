#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1（重测）：**按配对核**（pair_kernel=True）的平界面速度标定。

背景：上一轮用 `region()` 计数法判 `pair_kernel=True` = **0.000** ✗，据此把默认留在
`pair_kernel=False`。但计数法在亚胞平移下**失明**（见 `_chk_w2.py` 的记账），而且
本轮查清那条 0.000 另有真因：`band = (dist<=band_cells) & (karr==kat)` 把界面的
**runner-up 一侧整个排除** ⇒ 差分场 d 被拉陡而非平移（`LevelSetMulti.advance` 已修）。

本轮口径：**亚胞射线交点**（`iface_offset(..., near=a)`），周期自洽的 slab 初值。
判据：|v|/(MΔf) − 1| < 0.02。
扫描：(band_cells, iface_band) 全网格**如实报全部**，不挑好看的。
"""
import numpy as np
from windowB_surface import LevelSetMulti
import _chk_w2 as W2


def run_pk(band_cells=20, iface_band=1.0, nstep=40, N=48, adv_grad='upwind',
           herring=True):
    """pair_kernel=True 的 slab 速度 + 带健康度 + 差分场陡度。"""
    g = W2._seed(N, 2e-9, 'slab')
    near = g.near0
    _, z0 = g.iface_offset(1, 0, 2, near=near)
    dt = 0.1 * g.dx / (1e-9 * 1e7)
    for _ in range(nstep):
        g.advance(dt, extend='edt', band_cells=band_cells, pair_kernel=True,
                  iface_band=iface_band, adv_grad=adv_grad, herring=herring)
    _, z1 = g.iface_offset(1, 0, 2, near=near)
    v = abs(z1 - z0) / (nstep * dt) / (1e-9 * 1e7)
    ncell, med, ok = g.band_health()
    d = g.phi[1] - g.phi[0]
    gd = np.gradient(d, g.dx)
    gn = np.sqrt(sum(x ** 2 for x in gd))
    band = np.abs(d) <= 1.5 * g.dx * gn
    return v, ncell, med, ok, float(np.median(gn[band]) if band.any() else np.nan)


if __name__ == '__main__':
    print('---- P1 按配对核（pair_kernel=True）速度标定：亚胞射线交点口径 ----')
    print('%-6s %-7s %-10s %-10s %-8s %-8s' %
          ('band', 'iface', 'v/MDf', '判定', '带胞', '|grad|d|'))
    best = None
    for band in (6, 10, 20, 40):
        for ib in (1.0, 2.0, 3.0):
            v, nc, med, ok, gnm = run_pk(band_cells=band, iface_band=ib)
            good = abs(v - 1) < 0.02
            print('%-6d %-7.1f %-10.4f %-10s %-8d %-8.2f%s' %
                  (band, ib, v, 'PASS' if good else 'FAIL', nc, gnm,
                   '' if ok else '  [带不健康]'))
            if good and best is None:
                best = (band, ib, v)
    print()
    print('最优（若过）：', best)
    print('对照 pair_kernel=False :', W2.run())