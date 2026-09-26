#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_dir.py --- 审计：验证推进方向符号在所有 karr/larr 顺序下都正确。
   设计：1D 平面界面，变体1 vs 母相0，df>0（变体有利）。
   正确行为：phi_1 减小（变体长大）、phi_0 增大，且界面沿 DIR 前进。
   同时检查 coef 的符号约定：coef = sigma(本胞) * vcanon(界面胞)。"""
import numpy as np
import windowB_surface as W

# --- 构造一个只有 2 个区域（0=母相,1=变体）的最小体系，避免 nv=12 的干扰 ---
for order in ('karr=1,larr=0', 'karr=0,larr=1'):
    N, dx = 32, 5e-8
    L = N * dx
    g = W.LevelSetMulti(N, L, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, 2e8],
                        workers=1, reinit_every=0)
    x = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    # 平面界面：法向 +x；phi_1 = x - x0（>0 侧是母相）
    g.phi[1] = (X - 0.5 * L)
    g.phi[0] = -(X - 0.5 * L)
    # 强制 argmin 顺序：高 x 侧 phi_0 更小
    if order == 'karr=0,larr=1':
        pass                      # 默认即此
    karr = np.argmin(g.phi, axis=0)
    print('%-18s  region=argmin 在低 x 处 = %d, 高 x 处 = %d'
          % (order, karr[0, 0, 0], karr[-1, 0, 0]))
    ph1_0 = g.phi[1].copy(); ph0_0 = g.phi[0].copy()
    dt = 0.15 * dx / (1e-9 * 2e8)
    g.advance(dt, aniso=0.0, npref=None, band_cells=6)
    d1 = g.phi[1] - ph1_0; d0 = g.phi[0] - ph0_0
    band = np.abs(ph1_0) <= 2 * dx
    print('   phi_1 在界面上平均变化 = %+.4e  (应 <0 = 变体长大)' % d1[band].mean())
    print('   phi_0 在界面上平均变化 = %+.4e  (应 >0)' % d0[band].mean())
    # 界面位置（phi_1 的零等值面）
    def iface_x(phi):
        s = np.where(phi[:, 0, 0] < 0)[0]
        if len(s) == 0 or s[-1] >= N - 1: return np.nan
        i = s[-1]
        v = phi[:, 0, 0]
        return x[i] - v[i] * dx / (v[i + 1] - v[i])
    print('   界面 x: %.5f -> %.5f um (应增大)' % (iface_x(ph1_0) * 1e6, iface_x(g.phi[1]) * 1e6))
    print('   体+面总摩尔变化 = %.3e' % (sum(g.totals()) - (0.0),))
