#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_reinit.py --- R30 审计 S1：`reinitialize()`（`advance` 的收尾段）实测代价。

生产 `--reinit-dt 1e-4` ⇒ 每 ~600–1900 步触发一次；触发时**整步 wall 会跳一个量级**
（`_w2_cost_N96.log` 实测 step6 = 53.5 s vs 常态 2.9 s）。本脚本在 N=96 / 12 场下
直接量一次 `reinitialize(force=True)`，并给出 workers=1/4 的对比。

用法：python3 -u _r30_reinit.py [N] [w1,w4]
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
WLIST = ([int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2
         else [1, 4])
DX = 125e-9
GAMMA0 = 0.25
NLATH = 11

L = N * DX
laths = [1] * NLATH
lt = WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                  eps0_var=EPS0, npref_var=NPF, gamma0=GAMMA0)
eps0 = [np.asarray(lt.eps0[i], float) for i in range(len(laths))]
npref = {i + 1: np.asarray(lt.npref[i + 1], float) for i in range(len(laths))}
nv = len(eps0)
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=GAMMA0, Mob=MOB,
                    df=[0.0] + [DF] * nv, workers=1, reinit_every=0,
                    reinit_dt=None, reinit_band_cells=6.0, reinit_iters=100)
g.lath = lt
c0 = np.array([L / 2] * 3)
n_hab = np.asarray(NPF[1], float)
n_hab /= np.linalg.norm(n_hab)
a_ax = np.asarray(g.atab[1], float)
a_ax /= np.linalg.norm(a_ax)
T, Wd, Lp = 635e-9, 1224e-9, 4590e-9
for i in range(nv):
    off = (i - (nv - 1) / 2.0) * T
    g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T, elong=Lp / Wd,
                 along=a_ax, flat_end=True)
g.init_parent()
dt = 0.15 * g.dx / (MOB * DF)
kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05)
print('=' * 100)
print('_r30_reinit  N=%d  nreg=%d  reinit_iters=%d  reinit_band_cells=%s'
      % (N, g.nreg, g.reinit_iters, g.reinit_band_cells))
print('=' * 100, flush=True)
g.advance(dt, **kw)
phi0 = g.phi.copy()
for wk in WLIST:
    g.phi[:] = phi0
    g.par.set_threads(wk)
    g.par.stats = {}
    g._reinit_done = 0
    g._reinit_skipped = 0
    t0 = time.perf_counter()
    g.reinitialize(force=True)
    wall = time.perf_counter() - t0
    tot, stats = g.par.report()
    print('\nworkers=%d（生效 g.par.n=%d）  一次 reinitialize(force) = **%.3f s**'
          % (wk, g.par.n, wall))
    print('   做了 %d 个配对；跳过 %d；区域翻转 %d；带胞 %d -> %d'
          % (g._reinit_done, g._reinit_skipped,
             getattr(g, '_reinit_reg_flips_last', -1),
             g._reinit_band_before, g._reinit_band_after))
    print('   并行算子：%s' % {k: (v[1], v[2]) for k, v in stats})
g.par.close()
print('=' * 100)
