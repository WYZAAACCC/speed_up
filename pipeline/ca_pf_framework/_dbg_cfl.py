#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""隔离：**步长**（dt 折算的每步位移 cfl = dt·M|df|/dx）是不是 M2 塌缩的根因？
   现行 `M2_twelve_variants` 用 dt = 0.3dx/v，而 v = M|df|·**0.5** ⇒ 每步位移
   **0.6 dx**（不是 0.3）⇒ 一个 6dx 厚的板片 10 步就被吃光，一阶迎风在 0.6dx/步
   的冲击下必然失真。用法：_dbg_cfl.py <cfl> <nstep> [t_dx]
"""
import sys
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

cfl = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 25
t_dx = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
aniso, pk = 10.0, False
N, dx, df, gamma, Mob, rfrac = 32, 1e-8, -1e8, 0.15, 1e-9, 0.22
print('==== cfl=%.2f dx/步 nstep=%d 板厚=%.1fdx ====' % (cfl, nstep, t_dx))
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
dt = cfl * dx / (Mob * abs(df))
print('   %5s %7s %14s %12s %8s %10s' % ('step', '带胞', '|grad|中位', 'max', 'f_trans', '|grad|max全场'))
for s in range(nstep + 1):
    if s % 5 == 0 or s == nstep:
        karr = np.argsort(g.phi, axis=0)[0]
        phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
        gn = np.sqrt(sum(gi ** 2 for gi in np.gradient(phiw, g.dx)))
        A = g.cell_area_geom()
        m = A > 0
        vt = np.array([g.volume(j) for j in range(g.nreg)])
        print('   %5d %7d %14.3f %12.2f %8.4f %10.2f' %
              (s, int(m.sum()), float(np.median(gn[m])) if m.any() else np.nan,
               float(gn[m].max()) if m.any() else np.nan,
               1 - vt[0] / (N * dx) ** 3, float(gn.max())))
    if s == nstep:
        break
    g.advance(dt, aniso=aniso, npref=npref, pair_kernel=pk, iface_band=2.0)