#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r580_p1probe.py --- Q2 反常（materialized=0 / onfly=1.9e5）的**直接探针**。"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N, NV, DX, WORK = 40, 8, 0.0625, 4


def build(mode):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORK,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', pf_phi_mode=mode, h_chunk=4)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX
    for k in range(1, max(3, NV // 8) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    return g


for mode in ('materialized', 'onfly'):
    g = build(mode)
    print('======== %s ========' % mode)
    print('  elastic_soft = %r（类属性）' % getattr(g, 'elastic_soft', '<缺>'))
    print('  nreg=%d nv=%d  pf.phi.dtype=%s' % (g.nreg, g.nv, g.pf.phi.dtype))
    w = 1.5 * g.dx
    h = 0.5 * (1.0 - np.tanh(g.phi[1:] / w))
    print('  外部算的 h：min=%.6e max=%.6e  非零占比=%.4f'
          % (h.min(), h.max(), float((h != 0).mean())))
    reg = g.region()
    print('  region(): 各相胞数 %s' % np.bincount(reg.ravel(), minlength=g.nreg).tolist())
    ed = g.elastic_driving()
    print('  elastic_driving 之后：')
    print('    pf.phi.dtype=%s  max=%.6e  非零占比=%.4f'
          % (g.pf.phi.dtype, float(np.max(np.abs(g.pf.phi))),
             float((np.asarray(g.pf.phi) != 0).mean())))
    print('    pf._h_src=%s  pf._eps0_lag=%s'
          % ('None' if g.pf._h_src is None else 'set',
             'None' if g.pf._eps0_lag is None else
             'max=%.6e' % float(np.max(np.abs(g.pf._eps0_lag)))))
    e = g.pf.eps0_fields()
    print('    `eps0_fields()` 直接调：max=%.6e' % float(np.max(np.abs(e))))
    print('    `E_el()` = %.17e' % float(g.pf.E_el()))
    print('    ed（驱动）max=%.6e  非零占比=%.4f'
          % (float(np.max(np.abs(ed))), float((ed != 0).mean())))
    print()
