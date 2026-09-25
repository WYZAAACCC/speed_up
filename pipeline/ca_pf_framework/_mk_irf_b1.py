#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_mk_irf_b1.py --- 用**与生产同一套生成器**（verify_framework.kgt_given_V）生成 B1 的 IRF 表。

B0（现状）= k=0.6303, m=-818.4  ⇒ ΔT_0 = 17.93 K（现有 irf_ti64.csv）
B1（区间匹配，见 THERMO_F12_CLOSURE.md）= k=0.4713, m=-1170.4 ⇒ ΔT_0 = 47.3 K
其余公共：c0=0.036, D_L=9.5e-9, Γ=3.08e-7, G=1e6, μ_k=1.0
输出：irf_ti64_k047.csv（同格式：dT_K,V_m_per_s,R_tip_m）
"""
import io
import os
import numpy as np
from verify_framework import kgt_given_V, D_L, G_THERM, MU_K, C0_V

GAM = 3.08e-7
m_B1, k_B1 = 1170.4, 0.4713
HERE = os.path.dirname(os.path.abspath(__file__))
Vs = np.logspace(-3, 1, 201)
rows = []
for V in Vs:
    s = kgt_given_V(V, m_B1, k_B1, GAM, D_L, C0_V, G_THERM, MU_K)
    if s is not None:
        rows.append(s)
dT = np.array([r['dT'] for r in rows]); Vv = np.array([r['V'] for r in rows])
Rr = np.array([r['R'] for r in rows])
o = np.argsort(dT)
out = os.path.join(HERE, 'irf_ti64_k047.csv')
np.savetxt(out, np.column_stack([dT[o], Vv[o], Rr[o]]), delimiter=',',
           header='dT_K,V_m_per_s,R_tip_m', comments='')
print('B1 表: %d 点 ; dT = %.3f..%.3f K ; V = %.3e..%.3e m/s ; R = %.3e..%.3e m'
      % (len(dT), dT[o][0], dT[o][-1], Vv[o][0], Vv[o][-1], Rr[o][0], Rr[o][-1]))
print('写 -> %s' % out)
# 与 B0 表在**共同 ΔT 区间**上比 V
t0 = np.loadtxt(os.path.join(HERE, 'irf_ti64.csv'), delimiter=',', skiprows=1)
lo = max(t0[:, 0].min(), dT[o][0]); hi = min(t0[:, 0].max(), dT[o][-1])
print('共同 ΔT 区间 [%.2f, %.2f] K 上的 V 对比：' % (lo, hi))
print('   %-8s %-12s %-12s %-8s' % ('ΔT', 'V_B0', 'V_B1', 'V_B1/V_B0'))
for x in np.linspace(lo, hi, 7):
    v0 = float(np.interp(x, t0[:, 0], t0[:, 1]))
    v1 = float(np.interp(x, dT[o], Vv[o]))
    print('   %-8.2f %-12.4e %-12.4e %-8.2f' % (x, v0, v1, v1 / v0))