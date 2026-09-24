#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：M2 多界面塌缩的根因（三个只差一个因素的隔离实验）
   ① aniso=0 vs 10 —— 排除"Λ 越界/非凸 γ"
   ② 种子板厚 t = 2,4,6 dx —— 检查"薄板核心 φ≡0（退化初值）"
   ③ pair_kernel 0/1 —— 检查"按配对核"
用法：_dbg_m2band.py <aniso> <pair_kernel 0/1> <nstep> [t_dx]
"""
import sys
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants

aniso = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
pk = bool(int(sys.argv[2])) if len(sys.argv) > 2 else False
nstep = int(sys.argv[3]) if len(sys.argv) > 3 else 25
t_dx = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0

N, dx, df, gamma, Mob, rfrac = 32, 1e-8, -1e8, 0.15, 1e-9, 0.22
print('==== aniso=%g pair_kernel=%s nstep=%d 板厚 t=%.1f dx ===='
      % (aniso, pk, nstep, t_dx))
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
print('   %5s %7s %16s %12s %8s' % ('step', '带胞', '|grad phi_win|中位', 'max', 'f_trans'))
for s in range(nstep + 1):
    if s % 5 == 0 or s == nstep:
        karr = np.argsort(g.phi, axis=0)[0]
        phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
        gn = np.sqrt(sum(gi ** 2 for gi in np.gradient(phiw, g.dx)))
        A = g.cell_area_geom()
        m = A > 0
        vt = np.array([g.volume(j) for j in range(g.nreg)])
        print('   %5d %7d %16.3f %12.2f %8.4f' %
              (s, int(m.sum()), float(np.median(gn[m])) if m.any() else np.nan,
               float(gn[m].max()) if m.any() else np.nan, 1 - vt[0] / (N * dx) ** 3))
    if s == nstep:
        break
    g.advance(dt, aniso=aniso, npref=npref, pair_kernel=pk, iface_band=2.0)