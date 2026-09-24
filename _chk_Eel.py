#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_chk_Eel.py --- 10 行对照：E_el 是否真的能分辨"均匀/层片(孪晶/非孪晶)"'''
import numpy as np, sys
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from windowB_pf import C_iso, MartensitePF
C = C_iso(100e9, 0.3, 2); N, L = 64, 128e-9
eA = np.array([[0.06, 0.04], [0.04, -0.03]])
R = np.array([[0, -1.], [1, 0]])
eB = R @ eA @ R.T                       # 90° 旋转（孪晶对）
eX = np.array([[0.06, 0.0], [0.0, -0.03]])   # 非孪晶
def E(eps, lam=None, frac=0.5):
    pf = MartensitePF(N, L, C, np.array([eA, eps]), dim=2)
    if lam is None:
        pf.phi[0] = 1.0
    else:
        xx = np.arange(N)
        m = ((xx // lam) % 2 == 0).astype(float)[None, :] * np.ones((N, 1))
        pf.phi[0] = m; pf.phi[1] = 1 - m
    return pf.E_el()
print('均匀 eA              : %.6e J' % E(eA))
print('均匀 eB(旋转90°)     : %.6e J   （各向同性 C ⇒ 应与 eA 相等 ✓）' % E(eB))
print('均匀 eX              : %.6e J' % E(eX))
print('层片 孪晶对(λ=8)     : %.6e J' % E(eB, lam=8))
print('层片 非孪晶(λ=8)     : %.6e J' % E(eX, lam=8))
print('层片 孪晶对(λ=2)     : %.6e J   （应≈与 λ 无关）' % E(eB, lam=2))
print()
print('解析核对(均匀 eA): (V/2)eA:C:eA = %.6e J' % (
    0.5 * L**2 * np.einsum('ij,ijkl,kl->', eA, C, eA)))