#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断: 多相场和约束 Sum(phi)<=1 是否真的生效"""
import numpy as np
from windowB_pf3d import PF3D, C_iso3
from windowB_ti64_variants import variants
from windowB_rve3d import seed_variants

N, dx = 32, 2e-8
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
pf = PF3D(N, N * dx, C, eps0, gamma=0.15, w90=4 * dx, Lmob=0.7, dG=5e7, workers=1)
seed_variants(pf, vol_frac=0.12, rng=7)
print('初始 Sum(phi): max = %.4f   mean = %.4f' % (pf.phi.sum(0).max(), pf.phi.sum(0).mean()))
for s in range(6):
    f, _ = pf.forces()
    fp = pf.phi + 1.6e-10 * pf.Lmob * 0
    print('  step %d: f 的 min/max = %.3e / %.3e ; phi max = %.4f ; Sum 均值 = %.4f'
          % (s, f.min(), f.max(), pf.phi.max(), pf.phi.sum(0).mean()))
    pf.step(1.6e-10)
    S = pf.phi.sum(0)
    print('      step 后: Sum 的 min/mean/max = %.4f / %.4f / %.4f ; phi max = %.4f'
          % (S.min(), S.mean(), S.max(), pf.phi.max()))
    # 手工再验证一次 cap 语义
    a = np.arange(12, dtype=float).reshape(3, 4)
    m = np.array([True, False, True, False])
    b = a.copy(); b[:, m] /= b[:, m].sum(0)
    print('      [cap 语义自检] b[:,0] = %s (应为 [0.333,0.333,0.333])' % np.round(b[:, 0], 3))
