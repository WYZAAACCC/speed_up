#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_dbg_front.py --- 解 B1/B2 的根因：平面界面在驱动下的【体积分数增长】是否为正、是否线性于 Δf
用"变体体积分数随时间"（符号明确）测界面速度，避免 0.5 等值线的噪声。
'''
import numpy as np
import sys
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from windowB_pf import C_iso, MartensitePF

GAM, WW = 0.15, 8e-9
KAP, WBAR = 1.365 * GAM * WW, 13.18 * GAM / WW
dx = 2e-9
N = 128
L = N * dx
C = C_iso(100e9, 0.3, 2)
eps0 = np.zeros((1, 2, 2))
x = (np.arange(N) + 0.5) * dx
a = np.sqrt(KAP / (2 * WBAR))
print('平面界面诊断：dx=%.1f nm, 界面半宽 a=%.2f nm, W=%.2e, κ=%.2e' % (dx*1e9, a*1e9, WBAR, KAP))
print('%-10s %-10s %-12s %-12s %-12s' % ('L_trial', 'Δf(J/m3)', 't(s)', '体积分数', 'v=dF/dt·Lx'))
for Ltr in (1e-9, 1e-8):
    for df in (2e6, 8e6):
        pf = MartensitePF(N, L, C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM, dG=df)
        pf.W = WBAR; pf.Lmob = Ltr
        pf.phi[0] = 0.5 * (1 - np.tanh((x - 0.25 * L) / (2 * a)))
        dt = 1e-9
        f0 = pf.phi[0].mean()
        for _ in range(4000):
            pf.step(dt, cap_sum=False)
        f1 = pf.phi[0].mean()
        t = 4000 * dt
        v = (f1 - f0) * L / t                       # = 界面位移/时间（横截面积比例换成线速度）
        print('%-10.1e %-10.1e %-12.2e %-12.5f %-12.3e' % (Ltr, df, t, f1, v))