#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 B2: 为什么孪晶对/非孪晶对的 E_el 完全相同（可疑）"""
import numpy as np
from windowB_pf import C_iso, MartensitePF

N, L = 64, 2e-7
C = C_iso(100e9, 0.3, 2)
e0 = np.array([[0.06, 0.04], [0.04, -0.03]])
eB = np.array([[0.06, -0.04], [-0.04, -0.03]])
eX = np.array([[0.06, 0.00], [0.00, -0.03]])

for nm, eps in (('eB', eB), ('eX', eX)):
    pf = MartensitePF(N, L, C, np.array([e0, eps]), dim=2)
    xx = np.arange(N)
    m = ((xx // 8) % 2 == 0).astype(float)[None, :] * np.ones((N, 1))
    pf.phi[0] = m
    pf.phi[1] = 1 - m
    E = pf.E_el()
    ebar = m.mean() * e0 + (1 - m.mean()) * eps
    Ebar = 0.5 * L ** 2 * np.einsum('ij,ijkl,kl->', ebar, C, ebar)
    print('%s  填充率=%.4f  E_el=%.10e J  E_uniform=%.10e  E_fluct=%.6e'
          % (nm, m.mean(), E, Ebar, E - Ebar))

for nm, eps in (('eB', eB), ('eX', eX)):
    pf = MartensitePF(N, L, C, np.array([e0, eps]), dim=2)
    pf.phi[0] = 1.0
    print('单变体1 均匀:   E_el = %.10e J' % pf.E_el())
    pf2 = MartensitePF(N, L, C, np.array([e0, eps]), dim=2)
    pf2.phi[1] = 1.0
    print('单变体2(%s) 均匀: E_el = %.10e J' % (nm, pf2.E_el()))
