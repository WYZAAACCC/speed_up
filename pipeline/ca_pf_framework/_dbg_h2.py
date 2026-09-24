#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 H2：逐步打 R、界面胞数、实际翻转数，定位"径向速度被放大"的来源。
   理论：每步翻转胞数应 ≈ p·N_iface（p=|v|dt/dx），体积增量 ≈ 翻转数·dx^3，
         半径推进 = 体积增量/(4πR²)。把它与 p·dx 比较即可看出倍数。"""
import numpy as np
from windowB_hybrid import HybridBulkSurface, _sphere, DIRS6


def diag(N, dx, R0, M=1e-9, gamma=0.15, nshow=12):
    g = HybridBulkSurface(N, N * dx, gamma=gamma, M_int=M)
    m, r = _sphere(N, dx, R0)
    g.lab[m] = 1
    dt = 0.05 * dx / (M * 2 * gamma / R0)
    rng = np.random.default_rng(3)
    print('  N=%d dx=%.1f nm R0=%.1f nm (R0/dx=%.1f) dt=%.3e' % (N, dx * 1e9, R0 * 1e9, R0 / dx, dt))
    print('  %6s %9s %8s %9s %10s %12s %12s' %
          ('step', 'R(nm)', 'N_if', 'n_grow', 'p_meas', 'dR/dx', 'dR/(p*dx)'))
    for k in range(nshow):
        nprod = int((g.lab > 0).sum())
        R = (3 * nprod * dx ** 3 / (4 * np.pi)) ** (1 / 3)
        iface = g.iface_mask()
        nif = int((iface & (g.lab == 0)).sum())
        kap = g.curvature()
        vn = g.M * (0.0 + gamma * kap)
        p = np.clip(np.abs(vn) * dt / dx, 0, 1)
        ng, ns = g.advance(dt, df=0.0, rng=rng)
        if k % max(1, nshow // 6) == 0:
            nprod2 = int((g.lab > 0).sum())
            R2 = (3 * nprod2 * dx ** 3 / (4 * np.pi)) ** (1 / 3)
            dR = (R - R2) / dx
            pm = float(p[iface & (g.lab == 0)].mean())
            print('  %6d %9.2f %8d %9d %10.4f %12.4f %12.3f' %
                  (k, R * 1e9, nif, ng, pm, dR, dR / max(pm, 1e-9)))


if __name__ == '__main__':
    diag(64, 2e-9, 1.2e-8)
    diag(128, 1e-9, 1.2e-8)
