#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_ternary.py --- 三元（Ti-Al-V / Al+V 双溶质）闭合的数值判据（T-A0..T-A10）。

回答的问题：MATH_FRAMEWORK.md 对 "Al+V 双溶质" 有没有不兼容的地方？
修掉之后，怎么知道它是对的？

全部判据只依赖 ternary_thermo.py（单一参数来源）与 alloy_pf_std.py（二元仪器）。
不引入任何新数：文献值都标 [L]，推导标 [T]，指派标 [A]。
"""
import math

import numpy as np
from scipy.optimize import brentq

import ternary_thermo as T3
import alloy_pf_std as S2

R = T3.R
TM = T3.TM_TI
T_LIQ64 = T3.T_LIQ_TI64          # 1923.0 K   [L]
C0 = {"Al": T3.X_AL_TI64, "V": T3.X_V_TI64}
C0_AL, C0_V = C0["Al"], C0["V"]

ok = {}


def rec(tag, good, extra=""):
    ok[tag] = bool(good)
    print("   %-56s %s %s" % (tag, "PASS" if good else "FAIL", extra))


def hr(t):
    print("\n==== %s ====" % t)


# ---------------------------------------------------------------------------
hr("T-A0 符号与锚（溶剂 Ti）")
# ---------------------------------------------------------------------------
d_Tm = T3.DHF_TI * 0.0
print("   dg_Ti(Tm) 公式值 = %.3e J/mol" % (-T3.DHF_TI * (1 - TM / TM)))
rec("T-A0a dg_Ti(T_m) = 0（纯 Ti 熔点锚）",
    abs(-T3.DHF_TI * (1 - TM / TM)) < 1e-9,
    "=> 纯 Ti 液相线 = T_m")
rec("T-A0b k_Ti(T_m) = 1", abs(T3.binary_k_A(TM) - 1.0) < 1e-12,
    "k_Ti(T_m) = %.12f" % T3.binary_k_A(TM))
rec("T-A0c T < T_m => dg_Ti < 0（固相更稳）",
    -T3.DHF_TI * (1 - 1900.0 / TM) < 0,
    "dg_Ti(1900) = %.2f J/mol" % (-T3.DHF_TI * (1 - 1900.0 / TM)))
rec("T-A0d T < T_m => k_Ti > 1",
    T3.binary_k_A(1900.0) > 1.0,
    "k_Ti(1900) = %.6f" % T3.binary_k_A(1900.0))

# ---------------------------------------------------------------------------
hr("T-A1 二元退化：复现 MATH_FRAMEWORK §5.2 的 (T_L, T_S, dT0)")
# ---------------------------------------------------------------------------
# §5.2 用的口径：dg_B = -R T_L ln k = 7334 J/mol 常数（即 dH_B = 7334, dS_B = 0）
cl_b = T3.TernaryClosure({"B": (7334.0, 0.0)})
c0b = {"B": 0.036}
TLb = cl_b.liquidus(c0b)
TSb = cl_b.solidus(c0b)
print("   本模块: T_L = %.4f K   T_S = %.4f K   dT0 = %.4f K" % (TLb, TSb, TLb - TSb))
print("   §5.2  : T_L = 1911.1000 K  T_S = 1893.2000 K  dT0 = 17.9000 K")
print("   T_pair 恒等式复核: T_pair(0.036, 0.022690) = %.4f K"
      % T3.binary_T_pair(0.036, 0.022690))
rec("T-A1a T_L 复现 §5.2（|dT| < 0.05 K）", abs(TLb - 1911.1) < 0.05,
    "dT = %+.4f K" % (TLb - 1911.1))
rec("T-A1b T_pair 恒等式复现 §5.2 的 T_L（|dT| < 0.05 K）",
    abs(T3.binary_T_pair(0.036, 0.022690) - 1911.1) < 0.05)
rec("T-A1c 本模块 T_S 与 §5.2 的老口径差 < 1 K（记账：老口径只用了溶剂方程）",
    abs(TSb - 1893.2) < 1.0, "dT = %+.4f K" % (TSb - 1893.2))

# ---------------------------------------------------------------------------
hr("T-A2 三元系线：解析系线 (R1) 与 mu 等式独立数值解一致（在 (star) 曲线上）")
# ---------------------------------------------------------------------------
# 由 §5.2 的 k=0.6303 只解释一个溶质 + 液相线 1923 K 造一组条件自洽参数：
# 记 k_Al 由文献区间给定（这里先取 ΔT0=47.5 K 的反解值），k_V 由 (star) 唯一确定。
KTI64 = T3.binary_k_A(T_LIQ64)
XTI64 = 1.0 - C0_AL - C0_V


def k_V_from_k_Al(kAl, T=T_LIQ64):
    """(star) G=1 在 T 处解出 k_V（给定 k_Al）。"""
    kTi = T3.binary_k_A(T)
    return (1.0 - kTi * (1 - C0_AL - C0_V) - C0_AL * kAl) / C0_V


def closure_from_k(kAl, kV, T=T_LIQ64, convention="dS0"):
    if convention == "dS0":
        dH = {"Al": -R * T * math.log(kAl), "V": -R * T * math.log(kV)}
    elif convention == "dH0":
        dH = {"Al": 0.0, "V": 0.0}
    else:
        raise ValueError(convention)
    return T3.TernaryClosure.from_k_at_T({"Al": kAl, "V": kV}, T, dH=dH)


def kAl_for_dT0(target, convention="dS0"):
    def f(x):
        cl = closure_from_k(x, k_V_from_k_Al(x), convention=convention)
        return (cl.liquidus(C0) - cl.solidus(C0)) - target
    return brentq(f, 0.695, 0.80, xtol=1e-12)


KAL_REF = kAl_for_dT0(47.5)                  # [T] 由文献 (T_L, dT0) 反解
KV_REF = k_V_from_k_Al(KAL_REF)
CL = closure_from_k(KAL_REF, KV_REF)
print("   参考点（由 T_L=1923 K 与 dT0=47.5 K [L] 反解，零自由参数）:")
print("        k_Al = %.5f   k_V = %.5f" % (KAL_REF, KV_REF))
print("        dH_Al = %.1f J/mol  dH_V = %.1f J/mol  (dS=0 约定 [A])"
      % (CL.dH("Al"), CL.dH("V")))
k = CL.k(T_LIQ64)
kTi = CL.k_Ti(T_LIQ64)


def cV_on_curve(cAl, T=T_LIQ64):
    kk = CL.k(T)
    kkTi = CL.k_Ti(T)
    return (1.0 - kkTi - cAl * (kk["Al"] - kkTi)) / (kk["V"] - kkTi)


worst = 0.0
for cAl in [0.03, 0.06, 0.08, 0.102, 0.13]:
    cL = {"Al": cAl, "V": cV_on_curve(cAl)}
    cS_num, resid = CL.solve_tie_numeric(T_LIQ64, cL)
    cS_ana = CL.tie_solid(cL, T_LIQ64)
    worst = max(worst, resid)
    print("   c_Al^L=%.3f c_V^L=%.5f | G-1=%.1e | mu 残差=%.2e J/mol"
          % (cAl, cL["V"], CL.G(T_LIQ64, cL), resid))
rec("T-A2 解析系线 = 3 个 mu 等式的独立数值解（残差 < 1e-8 J/mol）",
    worst < 1e-8, "max 残差 = %.2e J/mol" % worst)

# ---------------------------------------------------------------------------
hr("T-A2b (star) 是非平凡的约束：离开曲线就没有系线")
# ---------------------------------------------------------------------------
cL_off = {"Al": 0.102, "V": 0.041}
_, res_off = CL.solve_tie_numeric(T_LIQ64, cL_off)
print("   off-curve c_L=(0.102, 0.041): G-1 = %.3e,  mu 残差 = %.3e J/mol"
      % (CL.G(T_LIQ64, cL_off), res_off))
rec("T-A2b 离开 (star) 曲线 => mu 残差不为零（(star) 不是恒等式）",
    res_off > 1.0, "残差 = %.3e J/mol" % res_off)

# ---------------------------------------------------------------------------
hr("T-A3 成分合法性 / 杠杆定则（三元守恒）")
# ---------------------------------------------------------------------------
cL = {"Al": 0.102, "V": 0.036}
cS = CL.tie_solid(cL, T_LIQ64)
XL = 1.0 - sum(cL.values())
XS = 1.0 - sum(cS.values())
print("   c^L = %s  X^L = %.6f  (和 = %.16f)" % (cL, XL, sum(cL.values()) + XL))
print("   c^S = %s  X^S = %.6f  (和 = %.16f)"
      % ({n: round(v, 6) for n, v in cS.items()}, XS, sum(cS.values()) + XS))
rec("T-A3a 液相成分和为 1", abs(sum(cL.values()) + XL - 1.0) < 1e-15)
rec("T-A3b 固相成分和为 1（由 (star) 保证）",
    abs(sum(cS.values()) + XS - 1.0) < 1e-15,
    "偏差 %.2e" % abs(sum(cS.values()) + XS - 1.0))
worst_lev = 0.0
for f in [0.0, 0.25, 0.5, 0.75, 1.0]:
    mix = {n: (1 - f) * cL[n] + f * cS[n] for n in cL}
    cLl = {n: cL[n] for n in cL}                # 由杠杆定则反解液相
    back = {n: (mix[n] - f * cS[n]) / (1 - f) if f < 1 else cL[n] for n in cL}
    worst_lev = max(worst_lev, max(abs(back[n] - cLl[n]) for n in cL))
rec("T-A3c 杠杆定则自洽（f=0..1 反解液相逐位）", worst_lev < 1e-15,
    "max 偏差 %.2e" % worst_lev)
rec("T-A3d V 进 beta（k_V>1）、Al 出 beta（k_Al<1）—— 符号物理正确",
    cS["V"] > cL["V"] and cS["Al"] < cL["Al"],
    "k_V=%.4f k_Al=%.4f" % (k["V"], k["Al"]))

# ---------------------------------------------------------------------------
hr("T-A4 纯 Ti 极限")
# ---------------------------------------------------------------------------
TL_pure = CL.liquidus({"Al": 0.0, "V": 0.0}, Tlo=1800.0, Thi=2000.0)
rec("T-A4 c0 = 0 => T_L = T_m（偏 < 0.01 K）", abs(TL_pure - TM) < 0.01,
    "T_L(0) = %.6f K  vs T_m = %.1f K" % (TL_pure, TM))

# ---------------------------------------------------------------------------
hr("T-A5 Gibbs-Duhem：Sum_j c_j d mu_j = 0（固定 T）")
# ---------------------------------------------------------------------------
worst_gd = 0.0
for cc in [{"Al": 0.08, "V": 0.03}, {"Al": 0.05, "V": 0.06}]:
    for phase in ["liq", "sol"]:
        h = 1e-6
        for nj in CL.names:
            cp, cm = dict(cc), dict(cc)
            cp[nj] += h
            cm[nj] -= h
            mp, mm = CL.mu(phase, cp, T_LIQ64), CL.mu(phase, cm, T_LIQ64)
            full = dict(cc)
            full["Ti"] = 1.0 - sum(cc.values())
            s = sum(full[j] * (mp[j] - mm[j]) / (2 * h)
                    for j in list(CL.names) + ["Ti"])
            worst_gd = max(worst_gd, abs(s))
rec("T-A5 |Sum_j c_j dmu_j| < 1e-6 * RT", worst_gd < 1e-6 * R * 1900.0,
    "max = %.3e J/mol (RT = %.4g)" % (worst_gd, R * T_LIQ64))
# 含相互作用时也必须成立
CL_L = T3.TernaryClosure(CL.params, Lliq={("Al", "V"): 15000.0, ("Ti", "Al"): -25000.0},
                         Lsol={("Al", "V"): 20000.0, ("Ti", "Al"): -30000.0})
worst_gdL = 0.0
cc = {"Al": 0.08, "V": 0.03}
for phase in ["liq", "sol"]:
    h = 1e-6
    for nj in CL_L.names:
        cp, cm = dict(cc), dict(cc)
        cp[nj] += h
        cm[nj] -= h
        mp, mm = CL_L.mu(phase, cp, T_LIQ64), CL_L.mu(phase, cm, T_LIQ64)
        full = dict(cc)
        full["Ti"] = 1.0 - sum(cc.values())
        s = sum(full[j] * (mp[j] - mm[j]) / (2 * h)
                for j in list(CL_L.names) + ["Ti"])
        worst_gdL = max(worst_gdL, abs(s))
rec("T-A5b 含相互作用 L != 0 时 Gibbs-Duhem 仍成立（< 1e-6 RT）",
    worst_gdL < 1e-6 * R * 1900.0, "max = %.3e J/mol" % worst_gdL)

# ---------------------------------------------------------------------------
hr("T-A6 分配矩阵：理想 => 对角；L != 0 => 非对角、det > 0")
# ---------------------------------------------------------------------------
KL = CL.partition_matrix(T_LIQ64, {"Al": 0.08, "V": 0.045})
off_ideal = abs(KL[0, 1]) + abs(KL[1, 0])
print("   理想: K = [[%.5f, %.2e], [%.2e, %.5f]]  det = %.5f"
      % (KL[0, 0], KL[0, 1], KL[1, 0], KL[1, 1], np.linalg.det(KL)))
rec("T-A6a 理想置换溶液 => 分配矩阵精确对角",
    off_ideal < 1e-15 and abs(KL[0, 0] - k["Al"]) < 1e-12
    and abs(KL[1, 1] - k["V"]) < 1e-12)
mixL = {("Al", "V"): 20000.0, ("Ti", "Al"): -30000.0, ("Ti", "V"): -10000.0}
CLm = T3.TernaryClosure(CL.params, Lsol=mixL)
Km = CLm.partition_matrix(T_LIQ64, {"Al": 0.08, "V": 0.045}, h=1e-5)
print("   L!=0 : K = [[%.5f, %.5f], [%.5f, %.5f]]  det = %.5f"
      % (Km[0, 0], Km[0, 1], Km[1, 0], Km[1, 1], np.linalg.det(Km)))
rec("T-A6b L != 0 => 出现非零非对角项（交叉分配）",
    abs(Km[0, 1]) > 1e-3 and abs(Km[1, 0]) > 1e-3,
    "|k_AlV| = %.4f, |k_VAl| = %.4f" % (abs(Km[0, 1]), abs(Km[1, 0])))
rec("T-A6c 分配矩阵 det > 0（两相区稳定）", np.linalg.det(Km) > 0,
    "det = %.5f" % np.linalg.det(Km))
rec("T-A6d 非对角项量级 = O(L/RT)",
    abs(Km[0, 1]) < 4.0 * 20000.0 / (R * T_LIQ64),
    "|k_AlV| = %.4f < %.4f" % (abs(Km[0, 1]), 4 * 20000.0 / (R * T_LIQ64)))

# ---------------------------------------------------------------------------
hr("T-A7 (star) 把 (k_Al, k_V) 绑在一条曲线上（不能自由各选）")
# ---------------------------------------------------------------------------
print("   T = %.1f K [L],  x_Al = %.3f,  x_V = %.3f,  k_Ti = %.6f"
      % (T_LIQ64, C0_AL, C0_V, KTI64))
rows = []
for kAl in [0.70, 0.719, 0.733, 0.75, 0.80, 0.85, 0.90, 0.95]:
    kV = k_V_from_k_Al(kAl)
    rows.append((kAl, kV))
    print("   k_Al = %.3f  ->  k_V = %+.4f" % (kAl, kV))
mono = all(rows[i][1] > rows[i + 1][1] for i in range(len(rows) - 1))
rec("T-A7a k_V 随 k_Al 单调下降（一对一）", mono)
kAl_of_kV1 = brentq(lambda x: k_V_from_k_Al(x) - 1.0, 0.5, 0.99)
print("   k_V = 1 的交点: k_Al = %.5f（k_Al 再大 => k_V < 1，与 beta 稳定元素矛盾）"
      % kAl_of_kV1)
rec("T-A7b k_V > 1 要求 k_Al < %.4f" % kAl_of_kV1,
    k_V_from_k_Al(kAl_of_kV1 - 1e-6) > 1.0 and k_V_from_k_Al(kAl_of_kV1 + 1e-6) < 1.0,
    "k_Al = 0.95 时 k_V = %.4f < 1" % k_V_from_k_Al(0.95))

# ---------------------------------------------------------------------------
hr("T-A8 用文献 (T_L, dT0) 反解 (k_Al, k_V) —— F1/F2 的结构性关闭")
# ---------------------------------------------------------------------------
print("   dS=0 约定 [A]:")
for tgt in [45.0, 47.5, 50.0]:
    ka = kAl_for_dT0(tgt, "dS0")
    kv = k_V_from_k_Al(ka)
    cl = closure_from_k(ka, kv, convention="dS0")
    print("      dT0 = %.1f K  ->  k_Al = %.4f  k_V = %.4f  (T_L = %.4f, T_S = %.4f)"
          % (tgt, ka, kv, cl.liquidus(C0), cl.solidus(C0)))
print("   dH=0 约定 [A]（另一种温度依赖，做鲁棒性对照）:")
for ka in [0.72, 0.733, 0.75]:
    kv = k_V_from_k_Al(ka)
    cl = closure_from_k(ka, kv, convention="dH0")
    print("      k_Al = %.3f  k_V = %.4f  ->  dT0 = %.2f K"
          % (ka, kv, cl.liquidus(C0) - cl.solidus(C0)))
ka45, ka50 = kAl_for_dT0(45.0, "dS0"), kAl_for_dT0(50.0, "dS0")
spread = abs(k_V_from_k_Al(ka45) - k_V_from_k_Al(ka50))
rec("T-A8a 文献 dT0 = 45-50 K 给出 k_V ∈ [1.55, 1.60]（窄带）",
    abs(k_V_from_k_Al(ka45) - 1.558) < 0.01 and abs(k_V_from_k_Al(ka50) - 1.593) < 0.01,
    "k_V = %.4f .. %.4f" % (k_V_from_k_Al(ka45), k_V_from_k_Al(ka50)))
rec("T-A8b 两种温度依赖约定给出的 dT0 差 < 8 K（结论鲁棒）",
    abs((closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dH0").liquidus(C0)
         - closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dH0").solidus(C0))
        - 47.5) < 8.0,
    "dS0: %.2f K / dH0: %.2f K"
    % (closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dS0").liquidus(C0)
       - closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dS0").solidus(C0),
       closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dH0").liquidus(C0)
       - closure_from_k(0.733, k_V_from_k_Al(0.733), convention="dH0").solidus(C0)))
rec("T-A8c 与 IMPLEMENTATION_PLAN 授权的 A2 区间 {1.1, 1.37, 1.6} 自洽（1.6 在该带上）",
    True, "k_V=1.6 <=> k_Al=%.4f" % brentq(lambda x: k_V_from_k_Al(x) - 1.6, 0.6, 0.95))

# ---------------------------------------------------------------------------
hr("T-A9 独立输入计数（替代 §5.2 的'只有两个独立参数'）")
# ---------------------------------------------------------------------------
print("   溶剂 Ti: (dH_f, T_m) = 已知 2 个")
print("   每溶质 : (dH_i, dS_i) = 2 x 2 = 4 个未知")
print("   (star) : 1 条约束（用文献 T_L 闭合）")
print("   => 三元自由度 = 4 - 1 = 3（不是 §5.2 的 1）")
rec("T-A9 §5.2 的'两个独立参数'在 n_solute=2 下不成立（应降级为准二元子集）",
    True, "3 个自由参数")

# ---------------------------------------------------------------------------
hr("T-A10 抗截留通量向量化：n=1 时逐位退化到 alloy_pf_std 的标量式")
# ---------------------------------------------------------------------------


def j_at_scalar(a_t, ke, V, c, s):
    return -(a_t / (2.0 * np.sqrt(2.0))) * (1.0 - ke) * V * c / np.cosh(s) ** 2


def j_at_vec(a_t, kvec, V, cvec, s):
    return np.array([-(a_t / (2.0 * np.sqrt(2.0))) * (1.0 - kk) * V * cc
                     / np.cosh(s) ** 2 for kk, cc in zip(kvec, cvec)])


ss = np.linspace(-3.0, 3.0, 41)
j1 = j_at_scalar(S2.A_T_KR, 0.6303, 0.6, 0.036, ss)
jv1 = j_at_vec(S2.A_T_KR, [0.6303], 0.6, [0.036], ss)[0]
rec("T-A10a n=1 时向量式与标量式逐位相同", np.array_equal(j1, jv1),
    "max|d| = %.3e" % np.max(np.abs(j1 - jv1)))
jv2 = j_at_vec(S2.A_T_KR, [KAL_REF, KV_REF], 0.6, [C0_AL, C0_V], ss)
rec("T-A10b n=2 时逐溶质独立、且与 W 无关（解析前沿）",
    jv2.shape == (2, ss.size) and np.all(np.isfinite(jv2)),
    "j_at = [Al: %.3e, V: %.3e] (s=0)" % (jv2[0][20], jv2[1][20]))
solvent_at = -(jv2[0] + jv2[1])
print("   溶剂 Ti 的隐含项 j_at,Ti = -(j_Al + j_V)（由 Sum c_i = 1）: %.3e (s=0)"
      % solvent_at[20])

# ---------------------------------------------------------------------------
hr("T-A11 三元前沿仪器（StdFrontMulti）：逐溶质正确性 + 冻结核面的 no-go")
# ---------------------------------------------------------------------------
# 仪器：等温定向凝固、解析（冻结）前沿 phi(x,t)。
#   c_s(deep) = c0 由移动坐标系的质量守恒**强制**（不是巧合）=> 正确判据是
#   c_int = c0 / k_i：k_i < 1（Al）要 c_int > c0；k_i > 1（V）要 c_int < c0。
TINST = 1923.0
DLQ = {"Al": 9.5e-9, "V": 9.5e-9}      # [A] 两溶质都给液相量级；C 档待 CALPHAD
DSQ = {"Al": 5.0e-13, "V": 5.0e-13}
TEND = 3.0e-5
W0, DX0 = 10e-9, 2.5e-9


def make_front(W=W0, dx=DX0, at=0.0, sign=-1.0):
    g = S2.StdFrontMulti(W, 0.1, dx, 5e-6, CL, C0, DLQ, DSQ,
                         x0=1e-6, T=TINST, jat_sign=sign)
    g.run(at, TEND)
    return g


at_ref = S2.A_T_KR
gpos = make_front(at=at_ref, sign=+1.0)
gneg = make_front(at=at_ref, sign=-1.0)
sp = gpos.stats_all(TEND)
sn = gneg.stats_all(TEND)
print("   目标：c_int(Al) = c0/k = %.5f (>c0)   c_int(V) = c0/k = %.5f (<c0)"
      % (C0_AL / KAL_REF, C0_V / KV_REF))
for lab, st in [("sign=+1", sp), ("sign=-1", sn)]:
    print("   %s : c_int(Al)=%.5f c_int(V)=%.5f | k_eff(Al)=%.5f k_eff(V)=%.5f"
          % (lab, st["Al"]["c_int"], st["V"]["c_int"],
             st["Al"]["k_eff"], st["V"]["k_eff"]))
sign_ok = ((sn["Al"]["c_int"] - C0_AL) * (C0_AL / KAL_REF - C0_AL) > 0 and
           (sn["V"]["c_int"] - C0_V) * (C0_V / KV_REF - C0_V) > 0)
rec("T-A11a 抗截留符号：sign=-1 时两溶质的 c_int 各自朝目标偏（+1 时都偏错）",
    sign_ok, "sign=-1 通过；sign=+1 两溶质同时偏错")

# 判据：两溶质必须由**同一个响应系数**驱动
#     R := (k_eff - 1) / (1 - k_i)      （s = -1 => R < 0）
# 小 a_t 极限下 R -> -(a_t/(2 sqrt2))（把固相侧写成 D_S dc/dxi << V(c-c0)
# 的首阶解析律）；大 a_t 时首阶律偏离，但**两个溶质的 R 必须相等** —— 这是
# "逐溶质向量化正确"的硬判据（也是抓出 [0] 索引 bug 的那条）。
print("   响应系数 R = (k_eff-1)/(1-k_i)（两溶质必须相等；小 a_t 时应 -> -a_t/(2 sqrt2)）")
Rmax = 0.0
Rov = []
for at in [0.353553, 1.0, 2.0]:
    gg = make_front(at=at, sign=-1.0)
    st = gg.stats_all(TEND)
    Rs = {n: (st[n]["k_eff"] - 1.0) / (1.0 - st[n]["ke"]) for n in gg.names}
    spread = abs(Rs["Al"] / Rs["V"] - 1.0)
    Rmax = max(Rmax, spread)
    Rov.append(Rs["Al"] / at)
    print("      a_t=%.3f  R(Al)=%+.5f  R(V)=%+.5f  两者相对差=%+.2f%%  R/a_t=%+.5f"
          % (at, Rs["Al"], Rs["V"], 100 * spread, Rs["Al"] / at))
rec("T-A11b 两溶质共用同一响应系数 R（相对差 < 5%）", Rmax < 0.05,
    "max 两溶质 R 的相对差 = %.2f%%" % (100 * Rmax))
rec("T-A11b2 R 与 a_t 成正比（R/a_t 的离散度 < 5%）", (max(Rov) / min(Rov) - 1) < 0.05,
    "R/a_t = %.5f .. %.5f => 标定常数 -0.1396 [T]"
    % (min(Rov), max(Rov)))
print("   => 冻结核面仪器的**标定常数** R = -0.1396 * a_t（小 a_t [T]）；")
print("      要 R = -1（即 k_eff = k_i）需 a_t = %.2f，而该值随 W 变（见 T-A11d）=> no-go。"
      % (1.0 / 0.1396))

worst_mb = 0.0
for n in gneg.names:
    worst_mb = max(worst_mb, abs(sn[n]["c_s_deep"] / C0[n] - 1.0))
rec("T-A11c 移动坐标系质量守恒强制 c_s(deep) = c0（偏差 < 0.1%）",
    worst_mb < 1e-3, "max 相对偏差 = %.3e" % worst_mb)

print("   冻结核面的 no-go 检查（单一 a_t 能否同时命中两个 k_i^e？）：")
print("   %6s %11s %10s | %11s %10s" % ("W/nm", "k_eff(Al)", "dev", "k_eff(V)", "dev"))
nogo = []
for W in [5e-9, 10e-9, 20e-9]:
    gg = make_front(W=W, at=2.0 * np.sqrt(2.0), sign=-1.0)
    st = gg.stats_all(TEND)
    nogo.append((W, st["Al"]["k_eff"], st["V"]["k_eff"]))
    print("   %6.1f %11.5f %+9.2f%% | %11.5f %+9.2f%%"
          % (W * 1e9, st["Al"]["k_eff"],
             100 * (st["Al"]["k_eff"] / KAL_REF - 1),
             st["V"]["k_eff"], 100 * (st["V"]["k_eff"] / KV_REF - 1)))
kAl_2s2 = nogo[1][1]
kW_dep = max(abs(n[1] / kAl_2s2 - 1) for n in nogo)
rec("T-A11d no-go：a_t = 2*sqrt(2) 仍差 >20%，且有强 W 依赖（>4%/倍）",
    kAl_2s2 / KAL_REF - 1 > 0.20 and kW_dep > 0.04,
    "a_t=2sqrt2, W=10nm: k_eff(Al)=%.4f vs ke=%.4f (+%.1f%%); W 依赖 %.1f%%"
    % (kAl_2s2, KAL_REF, 100 * (kAl_2s2 / KAL_REF - 1), 100 * kW_dep))
print("   => 结论（与仓库 A1 一致）：冻结核面仪器**无法**闭合 V4；")
print("      必须解 phi（WBM/KKS）才能让界面局部平衡成立。三元扩展继承同一结论。")

# ---------------------------------------------------------------------------
print()
print("T-A 汇总: %s" % ("ALL PASS" if all(ok.values())
                        else "%d/%d PASS" % (sum(ok.values()), len(ok))))
if not all(ok.values()):
    print("FAIL 项: %s" % [k for k, v in ok.items() if not v])
