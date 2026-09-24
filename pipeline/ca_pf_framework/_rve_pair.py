#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正对照: 只种【一对 rank-1 相容变体】的层片, 看 PF 能否给出干净板条。
   V1-V3 在法向 [0,1,0] 处 dE = 0（P3 已验证），故界面不花弹性能, 是"板条"的最干净工况。
   检查: 纯胞占比、界面剖面宽度(与 w90 比)、E_exc 与闭式。
"""
import numpy as np
from windowB_pf3d import PF3D, C_iso3, _lam_full
from windowB_ti64_variants import variants

N, dx = 96, 2e-9
L = N * dx
w90 = 4 * dx
dgr = 0.05
W = 13.183297 * 0.15 / w90
dG = dgr * W
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
A, B = 0, 2                      # V1, V3
n = np.array([0.0, 1.0, 0.0])
de = eps0[B] - eps0[A]
dE = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))
print('V%d-V%d 在 n=[0,1,0] 的 dE = %.4e J/m^3（0 = rank-1 相容）' % (A + 1, B + 1, dE))

pf = PF3D(N, L, C, eps0, gamma=0.15, w90=w90, Lmob=1.0, dG=dG, workers=8)
# 起始: 沿 y 的半空间层片（法向 y）
yy = (np.arange(N) + 0.5) * dx
slab = (yy < 0.5 * L)[None, :, None] * np.ones((N, N, N), bool)
pf.phi[:] = 0.0
pf.phi[A] = slab.astype(float)
pf.phi[B] = 1.0 - pf.phi[A]
# 标定迁移率
from windowB_rve3d import calibrate_L
Lmob, v1 = calibrate_L(pf, dG, 50.0)
pf.Lmob = Lmob
dt = 0.4 * dx / 50.0
print('L = %.4e (1D 标定 v(L=1) = %.3e m/s), dt = %.3e' % (Lmob, v1, dt))


def report(tag):
    s = pf.phi.sum(0)
    mx = pf.phi.max(0)
    tr = s > 0.5
    pure = (mx > 0.9) & tr
    Eb, Ec, Eg = pf.E_chem_grad()
    ph = np.fft.fftn(pf.phi[A]) / N ** 3
    S = float(np.sum(np.abs(ph) ** 2)) - abs(ph[0, 0, 0]) ** 2
    ebar = pf.phi[A].mean() * eps0[A] + pf.phi[B].mean() * eps0[B]
    Eexc = pf.E_el() - 0.5 * L ** 3 * np.einsum('ij,ijkl,kl->', ebar, C, ebar)
    Eclosed = 0.5 * L ** 3 * S * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))
    # 界面剖面宽度(10-90%)
    prof = pf.phi[B].mean(axis=(0, 2))
    y = (np.arange(N) + 0.5) * dx
    lo = np.interp(0.9, prof, y); hi = np.interp(0.1, prof, y)
    print('  [%s] 纯胞占比=%.3f  全局max_phi=%.3f  变体分数=%.3f/%.3f  '
          'E_exc=%.3e（闭式 %.3e）  界面 w90 实测=%.2f nm（设定 %.2f）'
          % (tag, pure.sum() / max(tr.sum(), 1), mx.max(), pf.phi[A].mean(), pf.phi[B].mean(),
             Eexc, Eclosed, (hi - lo) * 1e9, w90 * 1e9))
    return mx.max()


report('t=0')
for k in range(300):
    pf.step(dt)
    if (k + 1) % 100 == 0:
        report('step %d' % (k + 1))
