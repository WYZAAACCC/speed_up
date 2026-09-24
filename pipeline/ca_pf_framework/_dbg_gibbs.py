#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断: Gibbs 模型为什么完全不动? 提议为空 还是 接受被拒?"""
import numpy as np
from windowB_gibbs import GibbsLath
from windowB_pf3d import C_iso3
from windowB_ti64_variants import variants

N, dx = 32, 2e-9
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
g = GibbsLath(N, N * dx, C, eps0, gamma=0.15, df=5e7, workers=2, k0_mode='free')
v0 = 0
n0, e0 = g.favorable_normal(v0)
print('变体1 最省能法向 n* = %s ; 0.5 eps0:Lam(n*):eps0 = %.4e J/m^3' % (np.round(n0, 4), e0))
print('0.5 eps0:C:eps0      = %.4e J/m^3'
      % (0.5 * np.einsum('ij,ijkl,kl->', eps0[v0], C, eps0[v0])))
g.seed_plates(v0, n0, thick_cells=2, nplate=1, rng=0)
fv = np.count_nonzero(g.lab == v0 + 1) / g.lab.size
print('f_v1 = %.4f ; E_tot=%.4e (el %.4e, surf %.4e, chem %.4e)'
      % (fv, g.E_total(), g.E_el(), g.E_surf(), g.E_chem()))
vcell = g.dx ** 3
print('单胞: 化学增益 %.4e J ; 面能/键 %.4e J ; 弹性尺度 %.4e J'
      % (5e7 * vcell, 0.15 * g.dx ** 2, 0.1 * 1e9 * vcell))
sig = g.sigma()
iface = np.zeros_like(g.lab, bool)
for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
    iface |= (np.roll(g.lab, d, axis=(0, 1, 2)) != g.lab)
idx = np.argwhere(iface)
print('界面胞数 = %d' % len(idx))
for k in range(4):
    c = tuple(idx[k])
    old = g.lab[c]
    gs = np.array([sig[p][c] for p in range(6)])
    eo = g.zero if old == 0 else g.e0v_eng[old - 1]
    for nl in (0, 1, 2):
        if nl == old:
            continue
        en = g.zero if nl == 0 else g.e0v_eng[nl - 1]
        d_el = -vcell * float((en - eo) @ gs)
        d_ch = -5e7 * vcell * ((1 if nl > 0 else 0) - (1 if old > 0 else 0))
        d_sf = 0.15 * g.dx ** 2 * g._dsurf_local(c, int(old), nl)
        print('  cell%s old=%d -> %d : el=%+.3e ch=%+.3e sf=%+.3e sum=%+.3e'
              % (str(c), old, nl, d_el, d_ch, d_sf, d_el + d_ch + d_sf))
lab0 = g.lab.copy()
acc, dE = g.sweep(np.random.default_rng(0), nsel=2000)
print('sweep: 接受 %d, dE=%+.4e, lab 变化=%s' % (acc, dE, not np.array_equal(lab0, g.lab)))
