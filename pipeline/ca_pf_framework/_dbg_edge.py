#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""隔离：**全局重初始化**（Sussman 保亚胞位置）能否阻止 M2 远场 |∇φ| 自放大？
   机理假设：advection 用 |∇φ| ⇒ 跳变按 exp 自放大；而现行 `reinitialize` 的带宽仅 6dx，
   远场（`min_k φ_k` 的折点处）永不修复 ⇒ 放大累积 ⇒ 几何带静默塌缩。
用法：_dbg_edge.py <reinit_band_cells|0=关> <nstep>
"""
import sys
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

rb = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 25
aniso, pk, t_dx = 10.0, False, 6.0
N, dx, df, gamma, Mob, rfrac = 32, 1e-8, -1e8, 0.15, 1e-9, 0.22
print('==== 每步 reinitialize(band_cells=%g) nstep=%d ====' % (rb, nstep))
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
nv = len(eps0)
g = W.LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                    df=[0.0] + [df] * nv, workers=6, reinit_every=0)
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
dt = 0.3 * dx / (Mob * abs(df) * 0.5)
print('   %5s %7s %16s %12s %8s %8s' % ('step', '带胞', '|grad|中位', 'max', 'f_trans', 's'))
for s in range(nstep + 1):
    if s % 5 == 0 or s == nstep:
        karr = np.argsort(g.phi, axis=0)[0]
        phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
        gn = np.sqrt(sum(gi ** 2 for gi in np.gradient(phiw, g.dx)))
        A = g.cell_area_geom()
        m = A > 0
        vt = np.array([g.volume(j) for j in range(g.nreg)])
        print('   %5d %7d %16.3f %12.2f %8.4f %8.2f' %
              (s, int(m.sum()), float(np.median(gn[m])) if m.any() else np.nan,
               float(gn[m].max()) if m.any() else np.nan,
               1 - vt[0] / (N * dx) ** 3, float(gn.max())))
    if s == nstep:
        break
    g.advance(dt, aniso=aniso, npref=npref, pair_kernel=pk, iface_band=2.0)
    if rb > 0:
        g.reinitialize(band_cells=rb)