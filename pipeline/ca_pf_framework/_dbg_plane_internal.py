#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_plane_internal.py --- 打印 advance **内部**的 dG_cell / Mfac / v_cell（平界面三方向）。
   目的：把"速度几乎相同"分解成 (a) dG 本身不同  (b) Mfac 没生效。"""
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
    c0 = 0.5 * (proj.min() + proj.max())
    g.phi[k] = proj - c0
    g.init_parent(); g.c[:] = 0.036
    _M = 1e-9
    ed = g.elastic_driving()
    # --- 复现 advance 内部的量 ---
    reg = g.region()
    order = np.argsort(g.phi, axis=0); karr, larr = order[0], order[1]
    pha = np.take_along_axis(g.phi, karr[None], 0)[0]
    phb = np.take_along_axis(g.phi, larr[None], 0)[0]
    gd_ = np.gradient(pha - phb, dx)
    gdn = np.sqrt(sum(t ** 2 for t in gd_)) + 1e-30
    ndir = np.stack([t / gdn for t in gd_], -1)
    ndir = ndir / (np.linalg.norm(ndir, axis=-1, keepdims=True) + 1e-300)
    nd_ref = n1
    c2b = np.clip((ndir @ nd_ref) ** 2, 0, 1)
    c2w = np.clip((ndir @ w1) ** 2, 0, 1)
    Mfac = np.exp(-3.5 * c2b - 2.3 * c2w)
    nreg = g.nreg
    kap_all = np.stack([g.curvature_of(j) for j in range(nreg)])
    kap_cell = np.take_along_axis(kap_all, karr[None], 0)[0]
    stiff = np.full((nreg,) + reg.shape, g.gamma)
    stk = np.take_along_axis(stiff, karr[None], 0)[0]
    edk = np.take_along_axis(ed, karr[None], 0)[0]
    edl = np.take_along_axis(ed, larr[None], 0)[0]
    dG = (g.df[karr] - g.df[larr]) + (edk - edl) - stk * kap_cell
    band = np.abs(g.phi[k]) <= 1.5 * dx
    print('--- axis=%s  band cells=%d' % (axname, band.sum()))
    print('    dG_cell: mean %+.4e  |mean| %.4e  (max|.| %.4e)'
          % (dG[band].mean(), abs(dG[band].mean()), np.abs(dG[band]).max()))
    print('    Mfac   : mean %.5f  min %.5f  max %.5f' % (Mfac[band].mean(), Mfac[band].min(), Mfac[band].max()))
    print('    |v| = M*|dG|*Mfac : mean %.4e m/s' % (1e-9 * np.abs(dG[band])[np.abs(dG[band]) > 0].mean() if False else
          float(np.mean(1e-9 * np.abs(dG[band]) * Mfac[band]))))
    print('    ndir.nd_ref: mean |.| %.4f   ndir.nd_w: mean |.| %.4f'
          % (np.abs(ndir[band] @ nd_ref).mean(), np.abs(ndir[band] @ w1).mean()))
