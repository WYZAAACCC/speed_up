#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_plane_proj.py --- 直接测**零等值面的 proj 位置**随时间的移动（无几何因子）。
   对账：实测 dproj/dt  vs  dt 累积 * <v_cell>(0.5dx 带)。"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants(); nv = 12
rng = np.random.default_rng(0); npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best: best, bn = val, n
    npref[v + 1] = bn

N, dx = 48, 5e-8
L = N * dx
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')

for axname in ['n', 'w', 'a']:
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [2e8] * nv, workers=4, reinit_every=25)
    k = 1
    n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
    w1 = np.asarray(g.wtab[k], float)
    a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
    DIR = {'n': n1, 'w': w1, 'a': a1}[axname]
    proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
    g.phi[k] = proj - 0.5 * (proj.min() + proj.max())
    g.init_parent(); g.c[:] = 0.036
    # ★★ 隔离：**关掉弹性驱动**（ed 本身依赖界面取向 => 会污染 Mfac 的隔离）。
    #   wtab 已在 __init__ 用 C 建好；这里只把弹性求解器置空 => ed == 0。
    g.pf = None
    M = 1e-9
    ed = g.elastic_driving()
    dt = 0.15 * dx / (M * (2e8 + 2.0 * float(np.max(np.abs(ed)))))

    def pif():
        bnd = np.abs(g.phi[k]) <= 0.5 * dx
        return float(proj[bnd].mean()), int(bnd.sum())

    p0, n0 = pif()
    NN = 30
    tacc = 0.0
    for it in range(NN):
        g.advance(dt, aniso=0.0, npref=npref, band_cells=8, mob_beta=3.5, mob_beta_w=2.3)
        tacc += dt
    p1, n1c = pif()
    vmeas = (p1 - p0) / tacc
    print('axis=%s  cells %d->%d  proj %.5f -> %.5f um  over t=%.3e s'
          % (axname, n0, n1c, p0 * 1e6, p1 * 1e6, tacc))
    print('   v_meas = %+.4e m/s' % vmeas)
    print('   M*df   = %+.4e m/s   (纯化学驱动，不含 Mfac)' % (M * 2e8))
    print('   ratio v_meas/(M*df) = %+.4f' % (vmeas / (M * 2e8)))
