#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_plane_med.py --- 用**中位数**口径重测平界面速度（关弹性，纯 Mfac）。"""
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
res = {}
for axname in ['n', 'w', 'a']:
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [2e8] * nv, workers=4, reinit_every=0)
    k = 1
    n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
    w1 = np.asarray(g.wtab[k], float)
    a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
    DIR = {'n': n1, 'w': w1, 'a': a1}[axname]
    proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
    c0 = 0.5 * (proj.min() + proj.max())
    g.phi[k] = proj - c0
    g.init_parent(); g.c[:] = 0.036
    g.pf = None
    M = 1e-9
    dt = 0.15 * dx / (M * 2e8)

    def pmed():
        bnd = np.abs(g.phi[k]) <= 0.5 * dx
        return float(np.median(proj[bnd]))

    p0 = pmed(); tacc = 0.0
    for it in range(20):
        g.advance(dt, aniso=0.0, npref=npref, band_cells=8, mob_beta=3.5, mob_beta_w=2.3)
        tacc += dt
    p1 = pmed()
    v = (p1 - p0) / tacc
    Mfac = float(np.exp(-3.5 * (DIR @ n1) ** 2 - 2.3 * (DIR @ w1) ** 2))
    res[axname] = (v, Mfac)
    print('axis=%s  dproj(median) = %.5f um over %.3e s => v = %+.4e m/s' %
          (axname, (p1 - p0) * 1e6, tacc, v))
    print('     Mfac = %.4f  => 预期 v = %.4e m/s ; 实测/预期 = %.3f'
          % (Mfac, M * 2e8 * Mfac, v / (M * 2e8 * Mfac)))
print('\n比值（归一化到 a）:')
va = res['a'][0]
for kk in ['n', 'w', 'a']:
    print('   %s: v/v_a = %.4f   (Mfac 预期 %.4f)' % (kk, res[kk][0] / va, res[kk][1]))
