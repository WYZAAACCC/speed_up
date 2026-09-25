#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_irf2.py --- 量化 F1/F2（ΔT_0 的 17.9 vs 45~50 K）对 **Window A** 的影响

`_chk_thermo.py` 的结论：模型集 (k=0.6303, m=-818.4) 给 ΔT_0 = 17.93 K，与实测 45~50 K 冲突；
而在理想溶液+准二元族里**无法同时**满足实测液相线与实测区间（拟合区间会把液相线推到 -26 K）。
⇒ 现在唯一能做的定量判断：**把两套参数都代进 LKT，看 V(ΔT) 差多少**（这就是 Window A 的全部封闭律）。

对比两套（都由 van t Hoff + 模型闭式自洽）：
  B0 模型集：  k = 0.6303, m = -818.4 K/(mol frac), ΔT_0 = 17.93 K
  B1 区间集：  k = 0.4713, m = -1170.4 K/(mol frac), ΔT_0 = 48.0 K
其余公共：c0 = 0.036, D_L = 9.5e-9, Γ = 3.08e-7 K m, G = 1e6 K/m, μ_k = 1.0
"""
import math
import numpy as np
from scipy.special import exp1
from scipy.optimize import brentq

C0, DL, GAMMA, G, MU_K = 0.036, 9.5e-9, 3.08e-7, 1.0e6, 1.0


def iv(P):
    if P < 30.0:
        return P * math.exp(P) * exp1(P)
    return 1.0 - 1.0 / P + 2.0 / P ** 2 - 6.0 / P ** 3


def resid(V, R, K, ML):
    P = R * V / (2 * DL)
    cl = C0 / (1 - (1 - K) * iv(P))
    Gc = (V / DL) * cl * (1 - K)
    xi = 1 - 2 * K / (math.sqrt(1 + (2 * math.pi / P) ** 2) - 1 + 2 * K)
    arg = ML * Gc * xi - G
    return (2 * math.pi * math.sqrt(GAMMA / arg) - R) if arg > 0 else 1e9


def solve_R(V, K, ML):
    Rs = np.logspace(-9, -3, 500)
    prev = None
    for R in Rs:
        r = resid(V, R, K, ML)
        if r >= 1e8:
            prev = None
            continue
        if prev is not None and prev[1] * r < 0:
            return brentq(lambda x: resid(V, x, K, ML), prev[0], R, xtol=1e-18, rtol=1e-15)
        prev = (R, r)
    return None


def dT_of(V, K, ML):
    R = solve_R(V, K, ML)
    if R is None:
        return None, None
    P = R * V / (2 * DL)
    cl = C0 / (1 - (1 - K) * iv(P))
    return ML * (cl - C0) + 2 * GAMMA / R + V / MU_K, R


def V_of(dT, K, ML, lo=1e-4, hi=1.0):
    """给定 ΔT 求 V（单调，二分）"""
    def f(V):
        d, _ = dT_of(V, K, ML)
        return (d if d is not None else 1e3) - dT
    if f(lo) * f(hi) > 0:
        return None
    return brentq(f, lo, hi, xtol=1e-14, rtol=1e-13)


SETS = [('B0 模型集', 0.6303, 818.4), ('B1 区间集', 0.4713, 1170.4)]
print('==== 两套参数的 LKT 封闭对比（c0=0.036, D_L=9.5e-9, G=1e6, mu_k=1.0）====')
for tag, K, ML in SETS:
    Vc = G * K * DL / (ML * C0 * (1 - K))
    print('   %-10s k=%.4f  |m_L|=%.1f  ΔT_0=%.2f K  平面稳定极限 Vc=%.3e m/s'
          % (tag, K, ML, ML * C0 * (1 - K) / K, Vc))

print()
print('   %-10s %-12s %-12s %-10s' % ('ΔT (K)', 'V_B0 (m/s)', 'V_B1 (m/s)', '比值'))
for dT in (6.0, 8.0, 10.0, 12.0, 15.0, 17.5, 25.0, 35.0, 45.0):
    v0 = V_of(dT, 0.6303, 818.4)
    v1 = V_of(dT, 0.4713, 1170.4)
    s0 = ('%.4e' % v0) if v0 else '  无解'
    s1 = ('%.4e' % v1) if v1 else '  无解'
    r = ('%.2f' % (v1 / v0)) if (v0 and v1) else '  -'
    print('   %-10.1f %-12s %-12s %-10s' % (dT, s0, s1, r))

print()
print('   同一速度下的 ΔT（含 LPBF 工作点 V=0.1 m/s）：')
print('   %-12s %-12s %-12s %-10s' % ('V (m/s)', 'ΔT_B0 (K)', 'ΔT_B1 (K)', '差 (K)'))
for V in (0.01, 0.05, 0.1, 0.2, 0.5):
    d0, R0 = dT_of(V, 0.6303, 818.4)
    d1, R1 = dT_of(V, 0.4713, 1170.4)
    s0 = ('%.3f' % d0) if d0 else '  无解'
    s1 = ('%.3f' % d1) if d1 else '  无解'
    dd = ('%+.3f' % (d1 - d0)) if (d0 and d1) else '  -'
    print('   %-12.3f %-12s %-12s %-10s' % (V, s0, s1, dd))
print()
print('   可用的过冷度上限（= ΔT_0，IRF 表的 dT_hi）：B0 = 17.93 K ; B1 = 48.0 K')
print('   ⇒ Window A 的过冷度**可用区间**宽 2.7 倍；而 LPBF 工作点 ΔT 本身就在 10~17 K')
print('      ⇒ B0 会把工作点顶在"预算饱和"处（IRF 的 dT_hi = 17.97 K 正是 ΔT_0）✗')