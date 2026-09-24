#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位 M2 多界面塌缩：|grad phi_k| 在哪个场、哪类界面上爆掉？"""
import sys
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

aniso, pk, nstep, t_dx = 10.0, False, 4, 6.0
N, dx, df, gamma, Mob, rfrac = 32, 1e-8, -1e8, 0.15, 1e-9, 0.22
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
nv = len(eps0)
g = W.LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                    df=[0.0] + [df] * nv, workers=6, reinit_every=25)
npref = {}
rng = np.random.default_rng(0)
for v in range(nv):
    best = None
    bn = None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn
R = rfrac * N * dx
for v in range(nv):
    g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R,
                 t_dx * dx)
g.init_parent()
vv = Mob * abs(df) * 0.5
dt = 0.3 * dx / vv
karr0 = np.argsort(g.phi, axis=0)[0]
larr0 = np.argsort(g.phi, axis=0)[1]
print('初始 pair 组合（每胞 (karr,larr) 计数，前 8 个）:')
from collections import Counter
print(Counter(zip(karr0.ravel().tolist(), larr0.ravel().tolist())).most_common(8))
for s in range(1, nstep + 1):
    g.advance(dt, aniso=aniso, npref=npref, pair_kernel=pk, iface_band=2.0)
    karr = np.argsort(g.phi, axis=0)[0]
    larr = np.argsort(g.phi, axis=0)[1]
    print('--- step %d ---' % s)
    for k in range(g.nreg):
        gk = np.gradient(g.phi[k], g.dx)
        gn = np.sqrt(sum(x ** 2 for x in gk))
        bad = gn > 10
        if bad.any():
            print('   phi_%-2d max|grad|=%10.2f  坏胞=%6d  (其中 region==%d 的占 %d)'
                  % (k, gn.max(), bad.sum(), k, int(((karr == k) & bad).sum())))
    A = g.cell_area_geom()
    m = A > 0
    phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
    gnw = np.sqrt(sum(x ** 2 for x in np.gradient(phiw, g.dx)))
    print('   带胞=%6d 带内|grad|中位=%9.3f' % (int(m.sum()),
          float(np.median(gnw[m])) if m.any() else np.nan))