#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_irf.py --- V8 的 **CA 侧**独立核对：`irf_ti64.csv` 是不是真的 LKT 解？

V8 = 「CA 与 PF 在重合区给同一 V(ΔT)」。CA 的那一侧是查表 `irf_ti64.csv`（ExaCA 做法）。
本文件**按 MATH_FRAMEWORK §4.3 的方程从头实现 LKT**（不调用任何仓库代码），
再逐行核对表里的 (ΔT, V, R_tip) 是否满足：
  P = RV/(2D_L) ; Iv(P) = P e^P E1(P) ; c_l* = c0/(1-(1-k)Iv) ; G_c = (V/D_L)c_l*(1-k)
  ξ_c(P) = 1 - 2k/(sqrt(1+(2π/P)²) - 1 + 2k)
  R = 2π sqrt( Γ / (|m| G_c ξ_c - G) )              ← marginal stability（隐式，解 R）
  ΔT = |m|(c_l* - c0) + 2Γ/R + V/μ_k                ← 过冷度预算
判据：对表里每一行，用它的 V 反解 R_marg（应 ≈ 表里的 R_tip）、再算 ΔT_预算（应 ≈ 表里的 ΔT）。
"""
import math
import numpy as np
from scipy.special import exp1
from scipy.optimize import brentq

K = 0.6303
C0 = 0.036
DL = 9.5e-9
GAMMA = 3.08e-7          # K m   (γ_SL/ΔS_f,v)
ML = 818.0               # K/(mol frac)
G = 1.0e6                # K/m  （由 §4.3 的 Vc=5.5e-4 反推，见文档）
MU_K = 1.0               # m/(s K)（D6「μ_k 先取 1 m/(s K)」；§4.3 的 0.09 K @ V=0.1 是四舍五入）


def lkt_residual(V, R):
    P = R * V / (2 * DL)
    if P <= 0:
        return -R
    Iv = iv(P)
    cl = C0 / (1 - (1 - K) * Iv)
    Gc = (V / DL) * cl * (1 - K)
    den = math.sqrt(1 + (2 * math.pi / P) ** 2) - 1 + 2 * K
    xi = 1 - 2 * K / den
    arg = ML * Gc * xi - G
    return (2 * math.pi * math.sqrt(GAMMA / arg) - R) if arg > 0 else 1e9


def iv(P):
    """Iv(P) = P e^P E1(P)（Ivantsov）。P 大时 e^P 会溢出 ⇒ 用渐近式
       Iv ≈ 1 − 1/P + 2/P² − 6/P³（P≳30 时误差 <1e-12）。"""
    if P < 30.0:
        return P * math.exp(P) * exp1(P)
    return 1.0 - 1.0 / P + 2.0 / P ** 2 - 6.0 / P ** 3


def solve_R(V):
    # ★ 记账：不能用 [1e-9, 1e-3] 两端做 bracket —— arg<0 时我返回 +1e9，两端同号 ⇒ 误判"无解"
    #   （实测表内 ΔT=4.745 那几行被误报）。改为在 R 上**扫网格找变号**，并且只在 arg>0 的
    #   R 区间里找（arg≤0 ⇔ 低于平面界面稳定极限，物理上确实没有尖端解）。
    Rs = np.logspace(-9, -3, 400)
    prev = None
    for R in Rs:
        r = lkt_residual(V, R)
        if r >= 1e8:
            prev = None
            continue
        if prev is not None and prev[1] * r < 0:
            return brentq(lambda x: lkt_residual(V, x), prev[0], R, xtol=1e-18, rtol=1e-15)
        prev = (R, r)
    return None


def dT_budget(V, R):
    P = R * V / (2 * DL)
    Iv = iv(P)
    cl = C0 / (1 - (1 - K) * Iv)
    return ML * (cl - C0) + 2 * GAMMA / R + V / MU_K


tab = np.loadtxt("irf_ti64.csv", delimiter=",", skiprows=1)
print("---- 表: %d 行, ΔT ∈ [%.4f, %.4f], V ∈ [%.3e, %.3e], R_tip ∈ [%.3e, %.3e]"
      % (len(tab), tab[:, 0].min(), tab[:, 0].max(), tab[:, 1].min(), tab[:, 1].max(),
         tab[:, 2].min(), tab[:, 2].max()))
print("   %-9s %-11s %-11s %-9s %-11s %-10s" % ("ΔT表", "V表", "R_tip表", "P=RV/2D", "R_LKT(V表)", "ΔT_预算"))
rows = tab[::max(1, len(tab) // 12)]
worstR, worstT, np_ = 0.0, 0.0, 0
for dT, V, Rt in np.vstack([rows, tab[-1]]):
    R = solve_R(V)
    if R is None:
        print("   %-9.3f %-11.4e %-11.4e  （该 V 下无 marginal-stability 解）" % (dT, V, Rt))
        continue
    P = Rt * V / (2 * DL)
    dTb = dT_budget(V, R)
    eR = abs(R / Rt - 1.0)
    eT = abs(dTb / dT - 1.0)
    worstR, worstT, np_ = max(worstR, eR), max(worstT, eT), np_ + 1
    print("   %-9.3f %-11.4e %-11.4e %-9.4f %-11.4e %-10.4f  (R 偏 %+.1e, ΔT 偏 %+.1e)"
          % (dT, V, Rt, P, R, dTb, R / Rt - 1.0, dTb / dT - 1.0))
print("   ⇒ 全表最大偏差：R_tip %.3e ; ΔT %.3e  （核对行数 %d）" % (worstR, worstT, np_))
# 全表统计
eR = []; eT = []
for dT, V, Rt in tab:
    R = solve_R(V)
    if R is None:
        continue
    eR.append(R / Rt - 1.0); eT.append(dT_budget(V, R) / dT - 1.0)
print("   全表（%d 行）: max|R/R_tip-1| = %.3e ; max|ΔT_budget/ΔT-1| = %.3e"
      % (len(eR), np.max(np.abs(eR)), np.max(np.abs(eT))))
# 平面界面稳定极限与 V=0.1 工作点
Vc = G * K * DL / (ML * C0 * (1 - K))
print("   §4.3 参照: 平面界面稳定极限 Vc = %.4e m/s（框架写 5.5e-4）" % Vc)
V0 = 0.1
R0 = solve_R(V0)
print("   V=0.1 m/s ⇒ P=%.3f, R=%.4e m, ΔT_预算=%.3f K（框架写 P=1.80, R=0.34µm, ΔT=12.28）"
      % (R0 * V0 / (2 * DL), R0, dT_budget(V0, R0)))
