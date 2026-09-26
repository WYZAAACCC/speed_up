#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_mfac_ratio.py --- 审计：实测界面速度 / (M*|dG|*Mfac) 是否 = 1？
   若随界面取向或 |grad phi| 格式变化 => 存在**各向异性数值偏差**，
   它就是"被压制方向压制不够 => 等轴化"的候选来源。"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
g0 = W.LevelSetMulti(8, 8e-8, C=C, eps0=eps0, gamma=0.15, Mob=1e-9)
n1 = np.asarray([0.0, 0.0, 1.0]); w1 = np.asarray([1.0, 0.0, 0.0])  # 用轴向最干净
BH, BW = 3.5, 2.3

N, dx = 32, 5e-8
L = N * dx
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
print('%-8s %-9s %10s %10s %10s' % ('grad格式', 'DIR', 'v实测', 'v预测', '比值'))
for advg in ('upwind', 'central'):
    for nm, DIR in [('n_hab', np.array([0.0, 0.0, 1.0])),
                    ('w', np.array([1.0, 0.0, 0.0])),
                    ('a', np.array([0.0, 1.0, 0.0])),
                    ('tilt', np.array([0.577, 0.577, 0.577]))]:
        g = W.LevelSetMulti(N, L, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, 2e8],
                            workers=1, reinit_every=0)
        proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
        c0 = 0.5 * (proj.min() + proj.max())
        g.phi[1] = proj - c0
        g.phi[0] = -(proj - c0)
        g.pf = None                      # 关弹性：纯 Mfac 通道
        M = 1e-9
        dt = 0.15 * dx / (M * 2e8)
        # 界面位置（用 proj 的中位数）
        def pmed():
            b = np.abs(g.phi[1]) <= 0.5 * dx
            return float(np.median(proj[b]))
        p0 = pmed()
        # AUDIT-#4 验证：nv=1 时必须显式给 npref，否则无从构造参考取向
        _np1 = {1: np.array([0.0, 0.0, 1.0])}
        g.advance(dt, aniso=0.0, npref=_np1, band_cells=6, mob_beta=BH,
                  mob_beta_w=BW, adv_grad=advg)
        p1 = pmed()
        dproj = p1 - p0
        nd = g.normal()[0] if False else None
        # 解析 Mfac
        c2h = (DIR @ np.array([0.0, 0.0, 1.0])) ** 2
        c2w = (DIR @ np.array([1.0, 0.0, 0.0])) ** 2
        Mfac = float(np.exp(-BH * c2h - BW * c2w))
        v_pred = M * 2e8 * Mfac * dt
        print('%-8s %-9s %10.4e %10.4e %10.3f'
              % (advg, nm, dproj, v_pred, dproj / v_pred if v_pred else np.nan))
