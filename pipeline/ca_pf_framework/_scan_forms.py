#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""界面势 x k=0 约定 的 2x2 甄别: 从"完美相容层片"出发, 看哪种组合能保住纯板条。
   (obstacle, k0_mode) = (True/False) x ('clamped'/'free')
   判读: 纯胞占比应保持 ~1, 变体分数应保持 0.5/0.5, 母相应保持 ~0。
"""
import numpy as np
from windowB_pf3d import PF3D, C_iso3, _lam_full
from windowB_ti64_variants import variants

N, dx, nstep, dt = 48, 2e-9, 200, 2e-11
L = N * dx
w90 = 4 * dx
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
A, B = 0, 2
n = np.array([0.0, 1.0, 0.0])
yy = (np.arange(N) + 0.5) * dx
slab = (yy < 0.5 * L)[None, :, None] * np.ones((N, N, N), bool)
print('从完美相容层片 V%d/V%d (n=[0,1,0], dE=%.1e) 出发, %d 步 dt=%.1e'
      % (A + 1, B + 1, 0.5 * np.einsum('ij,ijkl,kl->', eps0[B] - eps0[A],
         _lam_full(C, n), eps0[B] - eps0[A]), nstep, dt))
for obs in (False, True):
    for k0 in ('free', 'clamped'):
        pf = PF3D(N, L, C, eps0, gamma=0.15, w90=w90, Lmob=1.0, dG=0.05 * 1e7,
                  workers=4, obstacle=obs, k0_mode=k0)
        pf.phi[:] = 0.0
        pf.phi[A] = slab.astype(float)
        pf.phi[B] = 1.0 - pf.phi[A]
        for _ in range(nstep):
            pf.step(dt)
        s = pf.phi.sum(0)
        mx = pf.phi.max(0)
        tr = s > 0.5
        pure = (mx > 0.9) & tr
        fA, fB = pf.phi[A].mean(), pf.phi[B].mean()
        print('  obstacle=%-5s k0=%-7s | 纯胞=%.3f max_phi=%.3f phi_V1=%.3f phi_V3=%.3f '
              'Sum=(%.3f,%.3f) W=%.2e kappa=%.2e'
              % (obs, k0, pure.sum() / max(tr.sum(), 1), mx.max(), fA, fB,
                 s.min(), s.max(), pf.W, pf.kappa), flush=True)
