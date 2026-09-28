#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_Eel_vs_t.py —— 探针：平板（圆柱盘 R=120nm）的 E_el 是否依赖厚度 t？

动机：`_audit_edsign2.py` 的 plate 档 dE/dR 精确为 0（E_el 6 位不变），
      与"改变厚度 3.3% 应可见"矛盾 ⇒ 先确认求解器到底看没看见形状变化。
正对照：同时扫**面内半径 R**（若 R 也不影响 ⇒ 求解器根本没吃几何 ⇒ 更大的 bug）。
"""
import os, sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
N, dx = 48, 2e-8
L = N * dx


def run(R, t, k0='clamped'):
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1e-9,
                        df=[0.0] * (len(eps0) + 1), workers=4,
                        reinit_every=0, k0_mode=k0)
    g.seed_plate(1, np.array([L / 2] * 3), np.array([0.0, 0.0, 1.0]), R, t)
    g.init_parent()
    reg = g.region()
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    ncell = int((reg == 1).sum())
    vol = ncell * dx ** 3
    E = float(g.pf.E_el())
    return ncell, vol, E


print('%-28s %-10s %-13s %-13s %-13s' %
      ('config', 'cells', 'vol(m3)', 'E_el(J)', 'E_el/vol(J/m3)'))
for t_nm in (60.0, 120.0, 124.0, 240.0):
    n, v, E = run(1.2e-7, t_nm * 1e-9)
    print('%-28s %-10d %-13.5e %-13.6e %-13.5e' %
          ('plate R=120nm t=%.0fnm' % t_nm, n, v, E, E / v))
print()
for R_nm in (60.0, 120.0, 180.0):
    n, v, E = run(R_nm * 1e-9, 1.2e-7)
    print('%-28s %-10d %-13.5e %-13.6e %-13.5e' %
          ('plate R=%.0fnm t=120nm' % R_nm, n, v, E, E / v))
print()
for R_nm in (90.0, 120.0, 150.0):
    n, v, E = run(R_nm * 1e-9, 2 * R_nm * 1e-9)   # 球等价（t = 2R）
    print('%-28s %-10d %-13.5e %-13.6e %-13.5e' %
          ('sphere-ish R=t/2=%.0fnm' % R_nm, n, v, E, E / v))
