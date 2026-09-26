#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_plane_step.py --- 单步对账：预测位移 dt*<v_cell> vs 实测位移 (dV/A)。"""
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
Aeff = L * L

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
    M = 1e-9
    ed = g.elastic_driving()
    dg_est = 2e8 + 2.0 * float(np.max(np.abs(ed)))
    dt = 0.15 * dx / (M * dg_est)
    V0 = float(g.volume(k))
    # 预测：界面上的 v_cell
    order = np.argsort(g.phi, axis=0); karr, larr = order[0], order[1]
    pha = np.take_along_axis(g.phi, karr[None], 0)[0]
    phb = np.take_along_axis(g.phi, larr[None], 0)[0]
    gd_ = np.gradient(pha - phb, dx)
    gdn = np.sqrt(sum(t ** 2 for t in gd_)) + 1e-30
    ndir = np.stack([t / gdn for t in gd_], -1)
    ndir = ndir / (np.linalg.norm(ndir, axis=-1, keepdims=True) + 1e-300)
    Mfac = np.exp(-3.5 * np.clip((ndir @ n1) ** 2, 0, 1) - 2.3 * np.clip((ndir @ w1) ** 2, 0, 1))
    nreg = g.nreg
    kap_all = np.stack([g.curvature_of(j) for j in range(nreg)])
    kap_cell = np.take_along_axis(kap_all, karr[None], 0)[0]
    stk = np.take_along_axis(np.full((nreg,) + g.phi.shape[1:], g.gamma), karr[None], 0)[0]
    edk = np.take_along_axis(ed, karr[None], 0)[0]
    edl = np.take_along_axis(ed, larr[None], 0)[0]
    dG = (g.df[karr] - g.df[larr]) + (edk - edl) - stk * kap_cell
    v_cell = M * dG * Mfac
    for bw, nm in [(2.0, '2.0dx'), (1.0, '1.0dx'), (0.5, '0.5dx')]:
        _if = np.abs(g.phi[k]) <= bw * dx
        print('   band %s: cells=%5d  <v>=%+.4e  med(v)=%+.4e  <dG>=%+.4e'
              % (nm, _if.sum(), v_cell[_if].mean(), np.median(v_cell[_if]), dG[_if].mean()))
    iface = np.abs(g.phi[k]) <= 0.5 * dx
    vmean = float(v_cell[iface].mean())
    vmed = float(np.median(v_cell[iface]))
    # 跑 1 步
    g.advance(dt, aniso=0.0, npref=npref, band_cells=8, mob_beta=3.5, mob_beta_w=2.3)
    dV = float(g.volume(k)) - V0
    dmeas = dV / Aeff
    dpred = dt * vmean
    print('axis=%s  dt=%.3e s' % (axname, dt))
    print('   iface 胞=%d  <v_cell>=%+.4e m/s  Mfac_med=%.4f  dG_mean=%+.4e'
          % (iface.sum(), vmean, np.median(Mfac[iface]), dG[iface].mean()))
    print('   预测位移(mean) = %.4e m ; 预测(med) = %.4e m ; 实测 = %.4e m ; 实测/预测mean = %.3f ; 实测/预测med = %.3f'
          % (dpred, dt * vmed, dmeas, dmeas / max(abs(dpred), 1e-30), dmeas / max(abs(dt * vmed), 1e-30)))
    print('   g.dG_max*M*dt/dx = %.4f (CFL 位移，应 <=0.15)'
          % (g.dG_max * M * dt / dx))
