#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_edsign.py --- 独立审计判据：**弹性能量释放率 vs 模型用的弹性驱动力 `ed`**。

问题：`LevelSetMulti.elastic_driving()` 返回 `ed = -eps0_v : sigma`（PF3D.forces/dfdphi 同）。
      而标准 Allen-Cahn / 界面力平衡给出的是
          delta F / delta eta_v = -eps0_v : sigma      （= 变分导数）
          界面驱动力 = + eps0_v : sigma                 （= 使能量下降的方向）
      两者**差一个符号**。本脚本用**有限差分能量释放率**独立判决哪一个对。

做法：单变体球，半径 R -> R+dR，用 `PF3D.E_el()` 量弹性能。
      界面每单位面积扫过 δV/δA 体积；能量释放率密度 = -(dE_el/dR)/(dA/dR)。
      与模型 `ed` 在界面带上的（面积加权）均值比较：**同号且同量级 = 符号正确**。
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


def E_of_R(R, k0, k=1):
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1e-9,
                        df=[0.0] * (len(eps0) + 1), workers=4, reinit_every=0,
                        k0_mode=k0)
    g.seed_sphere(k, [L / 2] * 3, R)
    g.init_parent()
    reg = g.region()
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    E = g.pf.E_el()
    return g, E, reg


for k0 in ('clamped', 'free'):
    R0 = 1.2e-7
    dR = 4e-9
    g, E0, reg = E_of_R(R0, k0)
    _, Ep, _ = E_of_R(R0 + dR, k0)
    _, Em, _ = E_of_R(R0 - dR, k0)
    dEdR = (Ep - Em) / (2 * dR)
    A = 4 * np.pi * R0 ** 2
    dAdR = 8 * np.pi * R0
    rel = -dEdR / dAdR                      # 正确的"能量释放率"驱动力 [J/m^3 * m = J/m^2 -> 需 /1]
    # 模型用的 ed
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    ed = g.elastic_driving()
    # 界面带（用 phi_1 的零等值面，球心 L/2）
    x = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    r = np.sqrt((X - L / 2) ** 2 + (Y - L / 2) ** 2 + (Z - L / 2) ** 2)
    band = np.abs(r - R0) <= 1.0 * dx
    ed_if = float(ed[1][band].mean())
    # 体积分数
    f = float((reg == 1).mean())
    print('---- k0_mode=%s ----' % k0)
    print('   R=%.1f nm  f=%.3f   V=%.3e m^3' % (R0 * 1e9, f, L ** 3))
    print('   E_el(R-dR)=%+.6e  E_el(R)=%+.6e  E_el(R+dR)=%+.6e  J' % (Em, E0, Ep))
    print('   dE_el/dR = %+.4e J/m  =>  界面每扫过 1 m 的能量变化 = %+.4e J/m' % (dEdR, dEdR / dAdR))
    print('   **正确的驱动力（能量下降为正） = -(dE/dR)/(dA/dR) = %+.4e J/m^3**' % rel)
    print('   **模型用的 ed = -eps0:sigma（界面带均值）      = %+.4e J/m^3**' % ed_if)
    if abs(rel) > 1e-12:
        print('   两者之比 ed/正确 = %+.3f   %s'
              % (ed_if / rel, '<<< 符号相反（差一个负号） >>>' if ed_if * rel < 0 else '同号'))
    print()
