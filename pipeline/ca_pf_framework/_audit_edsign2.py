#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_edsign2.py --- 弹性驱动力符号判决（修正归一化 + 平板几何 + 三种 k0 约定）。

正确的关系：把界面推进 dR，扫过体积 dV = A dR，总能量变化 dE。
模型里界面速度是 v = M * D，其中 D 的单位是 J/m^3。
能量守恒要求  D * dV = -dE   =>   D_correct = -(dE/dR)/(dA_area/dR 里的面积 A)
     （扫过体积对 R 的导数 = 界面面积 A(R)，不是 dA/dR！）
本脚本对**球**与**矩形平板**都算，并把模型返回的 `ed = -eps0:sigma` 在界面上取均值比较。
"""
import os, sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic
from windowB_ti64_variants import variants

N, dx = 48, 2e-8
L = N * dx
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
k = 1


def build(shape, R, k0, grow=0.0):
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1e-9,
                        df=[0.0] * (len(eps0) + 1), workers=4, reinit_every=0,
                        k0_mode=k0)
    c0 = np.array([L / 2] * 3)
    if shape == 'sphere':
        g.seed_sphere(k, c0, R + grow)
    else:
        n_h = np.asarray(g.wtab[k] * 0 + [0, 0, 1.0])       # 平板法向取 ẑ（任意，只为几何）
        g.seed_plate(k, c0, n_h, R, 1.2e-7 + grow)          # 厚度方向加厚
    g.init_parent()
    reg = g.region()
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    return g, g.pf.E_el(), reg


def area_of(reg, k=1):
    b = 0
    for ax in range(3):
        b += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return b * dx ** 2


for k0 in ('clamped', 'free'):
    for shape in ('sphere', 'plate'):
        R = 1.2e-7
        dR = 4e-9
        g, E0, reg0 = build(shape, R, k0)
        _, Ep, _ = build(shape, R, k0, +dR)
        _, Em, _ = build(shape, R, k0, -dR)
        dEdR = (Ep - Em) / (2 * dR)
        A = area_of(reg0)
        D_corr = -dEdR / A
        # 模型用的 ed
        ed = g.elastic_driving()
        ph1 = g.phi[1]
        band = np.abs(ph1) <= 1.0 * dx
        ed_if = float(ed[1][band].mean())
        ed_all = float(ed[1][reg0 == 1].mean())
        print('---- k0=%-8s shape=%-7s ----' % (k0, shape))
        print('   E(R-dR)=%+.5e  E(R)=%+.5e  E(R+dR)=%+.5e J' % (Em, E0, Ep))
        print('   dE/dR=%+.4e J/m ; A=%.4e m^2 ; dV/dR=A' % (dEdR, A))
        print('   **正确驱动力 D_corr = -dE/dV = %+.4e J/m^3**' % D_corr)
        print('   **模型 ed=-eps0:sigma  界面带均值=%+.4e  变体内均值=%+.4e**' % (ed_if, ed_all))
        print('   |比值| ed/D_corr = %+.3f  %s'
              % (ed_if / D_corr if D_corr else np.nan,
                 '<<< 符号相反 >>>' if ed_if * D_corr < 0 else '同号'))
        print()
