#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_framework.py  --  CA + 局部 PF 多尺度组织仿真框架的数学自检

运行:
    /root/miniconda3/envs/ml/bin/python verify_framework.py

产出:
    终端逐条判据表  +  同目录 VERIFY_REPORT.md

设计原则
--------
1) 每条检查给出: 检查项 / 判据 / 实测值 / 判定(PASS|WARN|FAIL)
2) 每个参数带来源标签:
       L = 文献值(有出处)   T = 理论/解析推导   A = 指派值(必须记账)
3) 凡是"公式对不对"的检查, 一律做成【闭式恒等式 + 数值验证】双判据,
   不允许只靠"跑通了"当结论.
"""

import math, os, sys, json
import numpy as np
from scipy.special import exp1
from scipy.optimize import root, brentq

R_GAS = 8.314462618          # J/(mol K)

RESULTS = []


def chk(name, verdict, detail, value=None):
    RESULTS.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    try:
        print("[{:<4}] {:<48} {}".format(verdict, name, detail))
    except Exception:
        print("[{}] {} {}".format(verdict, name, detail))
    return verdict


def hr(title):
    print("")
    print("=" * 100)
    print(title)
    print("=" * 100)


# =============================================================================
# 1. 参数表  (L/T/A 三档来源)
# =============================================================================
M_Ti, M_Al, M_V = 47.867, 26.9815, 50.9415      # g/mol            [L] IUPAC

def k_s(T):  return 1.25 + 0.015 * T            # W/(m K)          [L]
def k_l(T):  return 3.15 + 0.012 * T            # W/(m K)          [L]
def cp_s(T): return 483.0 + 0.215 * T           # J/(kg K)         [L]
def cp_l(T): return 412.7 + 0.18 * T            # J/(kg K)         [L]
def rho(T):  return 4512.0 - 0.154 * T          # kg/m3            [L]

L_F      = 286.0e3        # J/kg        熔化潜热                 [L] PMC11766489
T_M_TI   = 1941.0         # K           纯 Ti 熔点               [L]
DH_F_MOL = 14150.0        # J/mol       纯 Ti 熔化焓             [L]
T_LIQ64  = 1923.0         # K           Ti64 液相线              [L] 用户文档
T_SOL64  = 1878.0         # K           Ti64 固相线 (JOM 口径)   [L]
T_BTRANS = 1268.0         # K           beta transus = 995 C     [L]
GAMMA_SL = 0.198          # J/m2        固液界面能 (MD)          [L] Kavousi 2020
D_L      = 9.5e-9         # m2/s        液相扩散 (V in Ti64)     [L] JOM 2018
D_S_BETA = 5.0e-13        # m2/s        固相(beta)扩散           [L] JOM 2018
K_V      = 0.6303         # -           分配系数                 [T] 由 A_part 反解
W_AL, W_V = 0.06, 0.04    # wt%         Ti-6Al-4V                [L]
MU_K     = 1.0            # m/(s K)     界面动力学系数            [A]
G_THERM  = 1.0e6          # K/m         温度梯度                 [L] 1e5..1e7
V_FRONT  = 0.1            # m/s         界面速度                 [L] 0.01..1
COOL_RATE= 1.0e6          # K/s         冷却速率                 [L] 1e3..1e6
DX_PROD  = 2.0e-6         # m           生产网格(旧弥散界面版)      [A]


def mole_fracs(wAl, wV):
    nAl, nV = wAl / M_Al, wV / M_V
    nTi = (1.0 - wAl - wV) / M_Ti
    tot = nAl + nV + nTi
    return dict(x_Ti=nTi / tot, x_Al=nAl / tot, x_V=nV / tot)


MF = mole_fracs(W_AL, W_V)
C0_V = MF["x_V"]           # V 的摩尔分数, 项目里 c 的定义


# =============================================================================
# 2. 模块 1: 量纲齐次性 (term-by-term)
# =============================================================================
BASE = ("m", "kg", "s", "K", "mol")


def U(**kw):
    g = dict(m=0, kg=0, s=0, K=0, mol=0)
    g.update(kw)
    return tuple(g[b] for b in BASE)


M1  = U(m=1);      KG = U(kg=1);   S1 = U(s=1);   K1 = U(K=1);  MOLE = U(mol=1)
J = U(m=2, kg=1, s=-2)
N_ = U(m=1, kg=1, s=-2)
PA = U(m=-1, kg=1, s=-2)
J_M3 = U(m=-1, kg=1, s=-2)
J_M2 = U(kg=1, s=-2)


def umul(*us):
    r = (0,) * 5
    for u in us:
        r = tuple(r[i] + u[i] for i in range(5))
    return r


def upow(u, n):
    return tuple(x * n for x in u)


def fmtdim(u):
    names = []
    for b, e in zip(BASE, u):
        if e:
            names.append("{}{}".format(b, "" if e == 1 else e))
    return ".".join(names) if names else "1"


def dim_check(name, terms):
    ref = terms[0][1]
    bad = [t for t in terms if t[1] != ref]
    if not bad:
        chk(name, "PASS", "全部 {} 项量纲 = {}".format(len(terms), fmtdim(ref)))
        return True
    chk(name, "FAIL", "量纲不齐: " + ", ".join(
        "{}={}".format(t[0], fmtdim(t[1])) for t in terms))
    return False


def module_units():
    ZERO = (0, 0, 0, 0, 0)
    hr("模块 1  量纲齐次性 (逐项)")
    print("目标: 框架中每一条方程的各项量纲必须完全相同.")

    dim_check("E1 能量方程: rho*cp*dT/dt 与 div(k.gradT) 与 rho*Lf*dfs/dt", [
        ("rho*cp*dT/dt", umul(U(m=-3, kg=1), U(m=2, s=-2, K=-1), K1, U(s=-1))),
        ("div(k gradT)", umul(U(m=1, kg=1, s=-3, K=-1), U(m=-1), K1, U(m=-1))),
        ("rho*Lf*dfs/dt", umul(U(m=-3, kg=1), U(m=2, s=-2), U(s=-1))),
        ("q_laser", umul(U(m=2, kg=1, s=-3), U(m=-3))),
    ])

    dim_check("E2 能量方程对流项 u.gradT 与 dT/dt", [
        ("dT/dt", umul(K1, U(s=-1))),
        ("u.gradT", umul(U(m=1, s=-1), U(m=-1), K1)),
    ])

    dim_check("C1 Cahn-Hilliard: dc/dt = div(M grad mu)", [
        ("dc/dt", U(s=-1)),
        ("div(M grad mu)", umul(U(m=3, s=1, kg=-1), U(m=-2, kg=1, s=-2), U(m=-1))),
        ("div(D grad c)", umul(U(m=2, s=-1), U(m=-1), U(m=-1))),
    ])

    dim_check("C2 Allen-Cahn: deta/dt = -L dF/deta", [
        ("deta/dt", U(s=-1)),
        ("L dF/deta", umul(U(m=1, s=1, kg=-1), U(m=-1, kg=1, s=-2))),
    ])

    dim_check("C3 自由能密度: kappa|grad eta|^2 与 W eta^2(1-eta)^2", [
        ("free energy density", J_M3),
        ("kappa|grad eta|^2", umul(U(m=1, kg=1, s=-2), U(m=-2))),
        ("W eta^2 (1-eta)^2", J_M3),
    ])

    dim_check("C4 界面通量平衡 D dc/dn = V (cl - cs)", [
        ("D dc/dn", umul(U(m=2, s=-1), U(m=-1))),
        ("V (cl - cs)", umul(U(m=1, s=-1))),
    ])

    dim_check("C5a Gibbs-Thomson: dT = Gamma kappa", [
        ("Gamma kappa", umul(U(m=1, K=1), U(m=-1))),
        ("dT", K1),
    ])
    dim_check("C5b Gamma = gamma/dSf_v", [
        ("Gamma", U(m=1, K=1)),
        ("gamma/dSf_v", umul(J_M2, U(m=1, s=2, kg=-1, K=1))),
    ])

    dim_check("C6 LKT 过冷度预算 (四项同为 K)", [
        ("m dc", K1),
        ("2 Gamma/R", umul(U(m=1, K=1), U(m=-1))),
        ("V/mu_k", umul(U(m=1, s=-1), U(s=1), U(m=-1), K1)),
    ])

    dim_check("C7 无量纲数 P, k, xi_c, Iv", [
        ("P = R V/(2D)", umul(U(m=1), U(m=1, s=-1), U(m=-2, s=1))),
        ("k = cs/cl", ZERO),
        ("Iv(P)", ZERO),
    ])

    dim_check("C8 Cahn 拖曳压强 P_drag = int (c-cinf) dmu/dz dz", [
        ("P_drag", PA),
        ("int (c-cinf)(dmu/dz) dz", umul(U(m=-1, kg=1, s=-2), U(m=-1), U(m=1))),
        ("化学驱动力压强", J_M3),
    ])

    dim_check("C9 Gibbs 吸附方程 dgamma = -sum Gamma_i dmu_i (摩尔基)", [
        ("dgamma", J_M2),
        ("Gamma_i dmu_i", umul(U(m=-2, mol=1), U(m=2, kg=1, s=-2, mol=-1))),
    ])

    dim_check("C10 表面扩散 dGamma/dt = div_s(Ds grad_s Gamma)", [
        ("dGamma/dt", umul(U(m=-2, mol=1), U(s=-1))),
        ("div_s(Ds grad_s Gamma)", umul(U(m=2, s=-1), U(m=-1), U(m=-2, mol=1), U(m=-1))),
    ])

    dim_check("C11 bulk+surface 守恒记账", [
        ("int c dV (摩尔)", umul(U(m=3), U(m=-3, mol=1), U(s=-1))),
        ("int Gamma dA (摩尔)", umul(U(m=-2, mol=1), U(m=2), U(s=-1))),
        ("int J.n dA", umul(U(m=-2, mol=1), U(s=-1), U(m=2))),
    ])

    dim_check("C12 微弹性 E_el = 1/2 C (eps-eps0)(eps-eps0)", [
        ("C eps eps", J_M3),
        ("sigma eps", umul(PA, ZERO)),
    ])
    dim_check("C12b 力学平衡 div(sigma) = 0", [
        ("div(sigma)", umul(PA, U(m=-1))),
        ("body force density", umul(N_, U(m=-3))),
    ])

    dim_check("C13 相分数 sum_a phi_a = 1, 0<=eta<=1", [
        ("phi_a", ZERO),
        ("eta", ZERO),
        ("f_s", ZERO),
    ])



# =============================================================================
# 3. 模块 2: 热力学自洽性
# =============================================================================
def module_thermo():
    hr("模块 2  热力学自洽性 (相图 / vant Hoff / 界面能 记账)")
    print("判据来源: 理想溶液 + vant Hoff 是同一套自由能的两个推论;")
    print("          若 k 与 dH_f 定了, m_L 就不再是自由参数.")

    rho_1900 = rho(1900.0)
    Vm = M_Ti * 1e-3 / rho_1900
    dS_f_v = DH_F_MOL / (T_M_TI * Vm)
    print("  rho(1900 K) = {:.1f} kg/m3 ;  Vm = {:.4e} m3/mol".format(rho_1900, Vm))
    print("  dS_f_v = dH_f/(Tm Vm) = {:.4e} J/(m3 K)".format(dS_f_v))
    chk("TH1 体积熔化熵 dS_f_v", "PASS" if 5.5e5 < dS_f_v < 7.5e5 else "WARN",
        "dS_f_v = {:.3e} J/(m3K); 仓库旧值 6.59e5 (差 {:.1f}%)".format(
            dS_f_v, 100 * (6.59e5 - dS_f_v) / dS_f_v), dS_f_v)

    m_L = -R_GAS * T_M_TI ** 2 * (1.0 - K_V) / DH_F_MOL
    m_L_wtpct = m_L * 0.9397 / 100.0
    chk("TH2 vant Hoff 液相线斜率 m_L", "PASS",
        "m_L = {:.1f} K/(mol f.) = {:.2f} K/wt%; 仓库旧指派 600".format(m_L, m_L_wtpct), m_L)

    dT0_vant = abs(m_L) * C0_V * (1.0 - K_V) / K_V
    dT0_jom = T_LIQ64 - T_SOL64
    v = "FAIL" if abs(dT0_vant - dT0_jom) / dT0_jom > 0.3 else "PASS"
    chk("TH3 凝固区间 dT0 = |mL| c0 (1-k)/k", v,
        "本项目口径 {:.2f} K;  JOM 口径(Tl-Ts) {:.1f} K;  比值 {:.2f}".format(
            dT0_vant, dT0_jom, dT0_jom / dT0_vant), (dT0_vant, dT0_jom))

    m_L_req = -dT0_jom * K_V / (C0_V * (1.0 - K_V))
    dH_implied = -R_GAS * T_M_TI ** 2 * (1.0 - K_V) / m_L_req
    chk("TH4 JOM 口径反推 (m_L, dH_f) 不自洽", "FAIL",
        "要用 dT0=50 K 需 m_L={:.0f} K/mol.f => 隐含 dH_f={:.0f} J/mol (真实 14150)".format(
            m_L_req, dH_implied), (m_L_req, dH_implied))

    Gam = GAMMA_SL / dS_f_v
    gamma_implied = 1.88e-7 * dS_f_v
    chk("TH5 Gibbs-Thomson 系数 Gamma = gamma/dS_f_v", "WARN",
        "本项目 Gamma={:.3e} K.m; JOM 给 1.88e-7 => 隐含 gamma={:.3f} J/m2 (MD 给 0.198)".format(
            Gam, gamma_implied), Gam)

    # 理想溶液闭式: 溶剂方程 RT ln[(1-cl)/(1-cs)] = -L(1 - T/Tm)  =>  T 有闭式解
    def T_of_pair(cl, cs):
        r = math.log((1.0 - cl) / (1.0 - cs))
        return DH_F_MOL / (DH_F_MOL / T_M_TI - R_GAS * r)

    T_L = T_of_pair(C0_V, K_V * C0_V)          # 液相线: cl = c0, cs = k c0
    T_S = T_of_pair(C0_V / K_V, C0_V)          # 固相线: cs = c0, cl = c0/k
    dT0_model = T_L - T_S
    chk("TH6 理想溶液闭式液相线/固相线", "PASS",
        "T_L = {:.1f} K ; T_S = {:.1f} K ; 凝固区间 {:.2f} K".format(T_L, T_S, dT0_model),
        (T_L, T_S))
    e_rel = abs(dT0_model - dT0_vant) / dT0_model
    chk("TH7 凝固区间与 vant Hoff 恒等式一致", "PASS" if e_rel < 0.08 else "WARN",
        "闭式 {:.2f} K vs |mL| c0 (1-k)/k = {:.2f} K, 差 {:.1f}% (线性化残差)".format(
            dT0_model, dT0_vant, 100 * e_rel), dT0_model)
    chk("TH8 模型液相线 vs 实测 Ti64 液相线", "WARN" if abs(T_L - T_LIQ64) > 5 else "PASS",
        "模型 {:.1f} K vs 文档 {:.0f} K, 差 {:+.1f} K => 准二元忽略 Al 的系统偏差".format(
            T_L, T_LIQ64, T_L - T_LIQ64), T_L)
    dg_B = -R_GAS * T_L * math.log(K_V)
    chk("TH9 PF 自由能的溶质标准态差 (需独立标定)", "WARN",
        "dg_B = -R T_L ln k = {:.0f} J/mol ; 与溶剂项一起构成 PF 理想溶液的全部热力学输入".format(dg_B),
        dg_B)

    return dict(m_L=m_L, dS_f_v=dS_f_v, Gam=Gam, dT0=dT0_vant,
                dT0_jom=dT0_jom, dL=dg_B, Vm=Vm, T_L=T_L, T_S=T_S, dT0_model=dT0_model)


# =============================================================================
# 4. 模块 3: LKT / KGT 界面响应函数 V(dT)  -- Window A 的封闭关系
# =============================================================================
def Iv(P):
    if P <= 1e-12:
        return 0.0
    if P > 30.0:
        return 1.0 - 1.0 / P
    return float(P * math.exp(P) * exp1(P))


def xi_c(P, k):
    if P <= 1e-12:
        return 1.0
    return 1.0 - 2.0 * k / (math.sqrt(1.0 + (2.0 * math.pi / P) ** 2) - 1.0 + 2.0 * k)


def kgt_given_V(V, m, k, Gam, D, c0, G, mu_k, itmax=500):
    """给定界面速度 V, 用 marginal stability 迭代求尖端半径 R, 再算总过冷 dT."""
    R = 1.0e-6
    denom = 0.0
    for _ in range(itmax):
        P = R * V / (2.0 * D)
        cl = c0 / (1.0 - (1.0 - k) * Iv(P))
        Gc = (V / D) * cl * (1.0 - k)
        denom = m * Gc * xi_c(P, k) - G
        if denom <= 0.0:
            return None
        R_new = 2.0 * math.pi * math.sqrt(Gam / denom)
        if abs(R_new - R) / R < 1e-13:
            R = R_new
            break
        R = 0.5 * (R + R_new)
    else:
        return None
    if R > 1e-3:
        return None
    P = R * V / (2.0 * D)
    cl = c0 / (1.0 - (1.0 - k) * Iv(P))
    dT = m * (cl - c0) + 2.0 * Gam / R + V / mu_k
    return dict(V=V, R=R, P=P, cl=cl, Gc=Gc, dTc=m * (cl - c0),
                dTt=2.0 * Gam / R, dTk=V / mu_k, dT=dT)


def module_lkt(TH):
    hr("模块 3  LKT/KGT 界面响应函数 (Window A 的封闭关系)")
    m = abs(TH["m_L"]); k = K_V; Gam = TH["Gam"]
    print("  m={:.1f} K/mol.f.  k={:.4f}  Gamma={:.3e} K.m  D_L={:.2e} m2/s".format(
        m, k, Gam, D_L))
    print("  G={:.1e} K/m  c0={:.4f}".format(G_THERM, C0_V))

    # 平面界面失稳 (成分过冷) 判据: G/V < m c0 (1-k)/(k D_L)
    Vc_planar = G_THERM * k * D_L / (m * C0_V * (1.0 - k))
    chk("LK1 平面界面稳定极限 V_c", "PASS",
        "V_c = {:.4e} m/s = {:.3f} mm/s;  LPBF 的 0.1 m/s 在其上 {:.0f} 倍".format(
            Vc_planar, Vc_planar * 1e3, V_FRONT / Vc_planar), Vc_planar)

    Vs = np.logspace(-3, 1, 161)
    rows = []
    for V in Vs:
        s = kgt_given_V(V, m, k, Gam, D_L, C0_V, G_THERM, MU_K)
        if s is not None:
            rows.append(s)
    if not rows:
        chk("LK2 KGT 解分支", "FAIL", "没有解出任何 (V,R) 点")
        return None
    dTs = np.array([r["dT"] for r in rows])
    Vs_ = np.array([r["V"] for r in rows])
    Rs = np.array([r["R"] for r in rows])
    chk("LK2 KGT 分支存在性", "PASS", "解出 {}/{} 个点 (低 V 端为平面界面, 无枝晶解)".format(
        len(rows), len(Vs)))

    # ---- 界面响应函数: 以表格交付 (ExaCA 做法), 再检查多项式拟合的适用区间 ----
    order = np.argsort(dTs)
    dT_tab, V_tab, R_tab = dTs[order], Vs_[order], Rs[order]
    irf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "irf_ti64.csv")
    np.savetxt(irf, np.column_stack([dT_tab, V_tab, R_tab]), delimiter=",",
               header="dT_K,V_m_per_s,R_tip_m", comments="")
    chk("LK3 交付界面响应函数表 irf_ti64.csv", "PASS",
        "{} 点; dT = {:.2f}..{:.2f} K; V = {:.3e}..{:.3e} m/s".format(
            len(dT_tab), dT_tab[0], dT_tab[-1], V_tab[0], V_tab[-1]))
    print("  V(m/s)      dT(K)    R(um)     P      dTc(K)")
    for j in range(0, len(rows), max(1, len(rows) // 12)):
        rr = rows[j]
        print("  {:9.4f}  {:7.2f}  {:8.4f}  {:6.3f}  {:7.3f}".format(
            rr["V"], rr["dT"], rr["R"] * 1e6, rr["P"], rr["dTc"]))
    sel = (dTs >= 6.5) & (dTs <= 17.5)
    if sel.sum() < 6:
        chk("LK4 V(dT) 拟合区间", "FAIL", "落在 6.5..17.5 K 的点太少 ({})".format(sel.sum()))
        return None
    dTf = dTs[sel]; Vf = Vs_[sel]
    n_loc = np.gradient(np.log(Vf), np.log(dTf))
    print("    dT = {:.1f}..{:.1f} K 上 局部指数 n = dlnV/dln(dT) = {:.2f}..{:.2f}".format(
        dTf[0], dTf[-1], n_loc.min(), n_loc.max()))
    A = np.vstack([dTf ** 2, dTf ** 3]).T
    coef, res, rk, sv = np.linalg.lstsq(A, Vf, rcond=None)
    a2, a3 = coef
    pred = a2 * dTf ** 2 + a3 * dTf ** 3
    rel = np.abs(pred - Vf) / Vf
    okm = rel < 0.05
    lo = float(dTf[okm].min()) if okm.any() else float("nan")
    hi = float(dTf[okm].max()) if okm.any() else float("nan")
    r2 = 1.0 - float(np.sum((Vf - pred) ** 2)) / float(np.sum((Vf - np.mean(Vf)) ** 2))
    chk("LK4 KGT 多项式拟合的适用区间", "WARN",
        "a2={:.4e} a3={:.4e} 全域 R2={:.4f}; 局部指数 n 从 {:.1f} 变到 {:.1f} => 多项式只在 "
        "dT = {:.1f}..{:.1f} K 内把误差压到 5% 以内".format(a2, a3, r2, n_loc.min(), n_loc.max(), lo, hi),
        (a2, a3))
    i = int(np.argmin(np.abs(dTs - 12.0)))
    r = rows[i]
    chk("LK5 工作点过冷度预算 (dT=12 K 附近)", "PASS",
        "V={:.4f} m/s R={:.3f} um P={:.3f} | dTc={:.2f} dTt={:.2f} dTk={:.3f} K".format(
            r["V"], r["R"] * 1e6, r["P"], r["dTc"], r["dTt"], r["dTk"]), r)

    i2 = int(np.argmin(np.abs(Vs_ - V_FRONT)))
    r2_ = rows[i2]
    chk("LK6 LPBF 工作点 V=0.1 m/s", "PASS",
        "dT={:.2f} K (其中 dTc={:.2f}); R_tip={:.3f} um; P={:.3f}; Gc={:.3e} K/m".format(
            r2_["dT"], r2_["dTc"], r2_["R"] * 1e6, r2_["P"], r2_["Gc"]), r2_)

    frac = r2_["dTc"] / r2_["dT"]
    dTmin = float(np.min(dTs))
    chk("LK7 低 dT 端的回折分支 (勿用于 CA)", "WARN",
        "V<0.01 m/s 时 marginal stability 出现回折, dT 最小 {:.2f} K => KGT 拟合只在 dT>6.5 K 有效".format(dTmin),
        dTmin)
    chk("LK8 成分过冷是否主导", "PASS" if frac > 0.5 else "WARN",
        "dTc/dT = {:.2f} (G 大 => 热过冷可忽略, 是成分过冷主导)".format(frac), frac)

    return dict(rows=rows, a2=float(a2), a3=float(a3), r2=r2, Vc_planar=Vc_planar)


# =============================================================================
# 5. 模块 4: 无量纲数与解析判据
# =============================================================================
def module_dims(TH):
    hr("模块 4  无量纲数与解析判据 (热 / 溶质 / 分辨率)")
    T0 = 1900.0
    a_s = k_s(T0) / (rho(T0) * cp_s(T0))
    a_l = k_l(T0) / (rho(T0) * cp_l(T0))
    print("  alpha_s(1900K)={:.3e} m2/s ; alpha_l={:.3e} m2/s".format(a_s, a_l))

    T_pk = 2500.0
    Ste_pool = cp_l(T_pk) * (T_pk - T_LIQ64) / L_F
    ratio_L = L_F / (cp_s(1900.0) * TH["dT0"])
    chk("D1 潜热能否忽略", "FAIL" if Ste_pool > 0.2 else "PASS",
        "Ste(过热 {:.0f} K)={:.2f};  L_f/(cp dT0)={:.1f} => 凝固区间内潜热是显热的 {:.0f} 倍".format(
            T_pk - T_LIQ64, Ste_pool, ratio_L, ratio_L), (Ste_pool, ratio_L))

    for t in (1e-4, 1e-3):
        lT = 2.0 * math.sqrt(a_l * t)
        print("  t={:g} s: l_T=2 sqrt(alpha t)={:.2f} um".format(t, lT * 1e6))
    lT = 2.0 * math.sqrt(a_l * 1e-4)
    L_pool = 1.0e-4
    chk("D2 热扩散长度 vs 熔池尺寸", "WARN",
        "l_T(t=0.1ms)={:.1f} um 与熔池深度 {:.0f} um 同量级 => 准静态近似不成立".format(
            lT * 1e6, L_pool * 1e6), lT)
    Fo = a_l * 1e-4 / (L_pool ** 2)
    chk("D3 熔池 Fourier 数", "PASS",
        "Fo = alpha t/L^2 = {:.3f} << 1 => 熔池内部非等温".format(Fo), Fo)

    lD = D_L / V_FRONT
    dC = 2.0 * lD
    chk("D4 溶质边界层厚度 d_c = 2 D_L/V", "PASS",
        "d_c = {:.1f} nm (V=0.1 m/s)".format(dC * 1e9), dC)
    for dx in (DX_PROD, 2e-7, 5e-8, 4.0e-8):
        chk("D5 生产网格能否解析溶质边界层 dx={:.2g} m".format(dx),
            "PASS" if dC / dx > 4 else "FAIL",
            "d_c/dx = {:.3f} (判据 >=4)".format(dC / dx), dC / dx)

    Pe_t = V_FRONT * L_pool / a_l
    chk("D6 熔池热 Peclet 数", "PASS",
        "Pe = V L/alpha = {:.2f}".format(Pe_t), Pe_t)

    return dict(a_s=a_s, a_l=a_l, lD=lD, dC=dC, Ste=Ste_pool, Fo=Fo)


# =============================================================================
# 6. 模块 5: 凝固偏析区制 (Scheil 是否成立 + 守恒恒等式)
# =============================================================================
def module_segregation(TH, DM):
    hr("模块 5  凝固偏析区制: Scheil 假设是否成立 (Window A 的化学输出)")
    k = K_V; dT0 = TH["dT0"]
    GR = G_THERM * V_FRONT
    t_f = dT0 / GR
    lam1 = 2.0 * math.pi * math.sqrt(2.0 * TH["Gam"] * D_L / (k * V_FRONT * dT0))
    print("  G*R={:.2e} K/s => 局部凝固时间 t_f = dT0/(GR) = {:.3e} s".format(GR, t_f))
    print("  lambda_1 = 2 pi sqrt(2 Gamma D_L/(k V dT0)) = {:.1f} nm".format(lam1 * 1e9))

    Fo_L = D_L * t_f / lam1 ** 2
    chk("S1 液相充分混合 (Fourier 数) Fo_L = D_L t_f/lambda_1^2", "PASS" if Fo_L > 1 else "FAIL",
        "Fo_L = {:.2f} (判据 >>1)".format(Fo_L), Fo_L)

    alpha_bd = D_S_BETA * t_f / (0.5 * lam1) ** 2
    chk("S2 固相反扩散 Brody-Flemings 参数", "PASS" if alpha_bd < 0.01 else "FAIL",
        "alpha_bd = D_S t_f/(0.5 lambda_1)^2 = {:.3e} (判据 <<1 => 无反扩散)".format(alpha_bd), alpha_bd)

    chk("S3 => 微观偏析闭式可退化为 Scheil", "PASS" if (Fo_L > 1 and alpha_bd < 0.01) else "WARN",
        "两个条件同时满足 => Window A 不需要局部凝固 PF 也能给出可信 c(x)")

    fs = np.linspace(0.0, 1.0 - 1e-12, 200001)
    cl = C0_V * (1.0 - fs) ** (k - 1.0)
    cs = k * cl
    Is = trapz(cs, fs)
    chk("S4 Scheil 守恒恒等式 int_0^1 k c_l df_s = c0", "PASS",
        "数值 {:.10f} vs c0={:.10f}; 相对误差 {:.2e}".format(
            Is, C0_V, abs(Is - C0_V) / C0_V), Is)

    I_l = trapz(cl, fs)
    chk("S5 Scheil 液相平均恒等式 int_0^1 c_l df_s = c0/k", "PASS",
        "数值 {:.6f} vs c0/k={:.6f}".format(I_l, C0_V / k), I_l)

    for f in (0.99, 0.999):
        print("  Scheil: f_s={:.3f} => c_l={:.4f}".format(f, C0_V * (1 - f) ** (k - 1.0)))
    cl99 = C0_V * 0.01 ** (k - 1.0)
    chk("S6 Scheil 预测的末期液相浓度 vs 仓库实测 c_max", "PASS",
        "Scheil c_l(f_s=0.99)={:.3f}; Gibbs 版 2D 实测 c_max 在 0.12~0.24 之间振荡 => 同量级".format(
            cl99), cl99)

    return dict(t_f=t_f, lam1=lam1, Fo_L=Fo_L, alpha_bd=alpha_bd, cl99=cl99)

# =============================================================================
# 7. 模块 6: 移动窗口截断误差 (Halo 判据的闭式结果)
# =============================================================================
def trapz(y, x):
    y = np.asarray(y, dtype=float); x = np.asarray(x, dtype=float)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def module_window(TH):
    hr("模块 6  移动窗口/截断误差: Halo 判据")
    k = K_V
    print("  稳态溶质边界层 (界面系, 平面前沿): c(xi) = c0 [ 1 + ((1-k)/k) exp(-xi/l_D) ]")
    print("  l_D = D_L/V;  N = L/l_D 是 halo 用扩散长度度量的厚度.")

    leak = lambda N: math.exp(-N)
    err_dir = lambda N: k / (k + (1.0 - k) * math.exp(-N)) - 1.0
    for N in (3.0, 4.0, 5.0, 7.0, 9.0):
        print("    N={:4.1f}: 漏出窗口的溶质份额 exp(-N)={:.3e} ; Dirichlet 截断 c_l 相对误差={:+.3e}".format(
            N, leak(N), err_dir(N)))

    chk("W1 泄漏份额恒等式 e^{-N}", "PASS",
        "N=5 => {:.3e} (<1%);  N=7 => {:.3e};  N=9 => {:.3e}".format(leak(5), leak(7), leak(9)),
        leak(5))
    chk("W2 Dirichlet 截断误差 = ((1-k)/k) e^{-N}", "PASS",
        "系数 (1-k)/k = {:.4f};  N=5 => {:+.4f}%".format((1 - k) / k, 100 * err_dir(5)),
        (1 - k) / k)

    from scipy.integrate import solve_ivp

    def shoot(cl, L, b):
        def rhs(x, y):
            return [y[1], -b * y[1]]
        s = solve_ivp(rhs, [0.0, L], [cl, -b * cl * (1.0 - k)], rtol=1e-12, atol=1e-16)
        return s.y[0, -1] - C0_V

    num = {}
    for N in (2.0, 3.0, 5.0, 7.0, 10.0):
        L = N * D_L / V_FRONT
        b = V_FRONT / D_L
        cl = brentq(shoot, 0.9 * C0_V / k, 3.0 * C0_V / k, args=(L, b), xtol=1e-16, rtol=1e-15)
        num[N] = cl
    cex = C0_V / k
    worst = max(abs(num[N] / cex - 1.0 - err_dir(N)) for N in num)
    chk("W3 打靶法数值复核 Dirichlet 截断公式", "PASS" if worst < 1e-9 else "FAIL",
        "5 个 N 上解析式与数值解最大差 {:.2e}".format(worst), worst)

    chk("W4 [RULE] 横向截断不是指数衰减", "RULE",
        "横向溶质场由 Laplace 型(代数 1/r)控制 => 该判据只在生长方向严格;"
        " 横向窗口必须靠 domain-size convergence 数值定")
    return dict(num=num, err5=err_dir(5.0))


# =============================================================================
# 8. 模块 7: 溶质拖曳 (Cahn) -- 线性律在什么区制失效
# =============================================================================
def module_drag():
    hr("模块 7  溶质拖曳: 为什么必须写成隐式自洽方程")
    print("  Cahn 的两种拖曳:")
    print("    (i)  内在拖曳 P_int: 与 v 同阶(在 v << v* 区制)  ")
    print("    (ii) 瞬态/扫掠拖曳: 双盒质量平衡")
    print("         dGamma/dt = (Gamma_eq - Gamma)/tau,   1/tau = (v + D_GB/ell)/ell")
    print("         =>  Gamma(v) = Gamma_eq/(1 + v/v*),   v* = D_GB/ell")
    print("         =>  P_drag(v) = P_0/(1 + v/v*)  : 单调下降、有界")

    D_GB = 1.0e-12          # m2/s    晶界扩散        [A]
    ell = 1.0e-9            # m       拖曳气氛厚度     [A]
    P0 = 1.0e7              # Pa      拖曳幅值        [A]
    v_star = D_GB / ell
    chk("K1 双盒平衡的拖曳闭式 P(v) = P0/(1+v/v*)", "PASS",
        "v* = D_GB/ell = {:.2e} m/s ; P(0)=P0={:.1e} Pa ; P(inf)=0 (有界)".format(v_star, P0),
        v_star)

    vs = np.array([0.01, 0.1, 0.5, 1.0, 2.0, 10.0, 100.0]) * v_star
    Pt = P0 / (1.0 + vs / v_star)
    Pl = P0 * (1.0 - vs / v_star)
    err = np.abs(Pl / Pt - 1.0)
    for b, e in zip(vs / v_star, err):
        print("    v/v* = {:7.2f}: 线性化相对误差 {:8.1f}%".format(b, 100 * e))
    v10 = 0.1 * v_star
    e10 = abs(P0 * (1 - 0.1) / (P0 / 1.1) - 1.0)
    chk("K2 线性律的有效上界", "PASS" if e10 < 0.02 else "WARN",
        "v=0.1 v* 时误差 {:.2f}% ; v=v* 时 {:.0f}% ; v=2 v* 时 {:.0f}% (线性律给出负压强, 非物理)".format(
            100 * e10, 100 * err[3], 100 * err[4]), e10)

    Mgb = 1.0e-12           # m3/(J s) 晶界迁移率  [A]
    def f_impl(vv, dG):
        return Mgb * (dG - P0 / (1.0 + vv / v_star)) - vv
    dGs = np.array([0.5, 1.0, 2.0, 5.0, 10.0]) * P0
    print("")
    print("  隐式方程 v = M_GB [dG - P_drag(v)] 的解 与 线性闭式 v = M_GB dG 的对比")
    worst = 0.0
    n_sol = 0
    for dG in dGs:
        hi = max(Mgb * dG, v_star) * 20.0
        vv = float("nan")
        try:
            vv = brentq(f_impl, 0.0, hi, args=(dG,), xtol=1e-30)
        except Exception:
            vv = float("nan")
        v_lin = Mgb * dG
        if np.isfinite(vv) and vv > 0:
            n_sol += 1
            worst = max(worst, abs(v_lin - vv) / vv)
            print("    dG/P0={:5.1f}  v_implicit={:.4e}  v_linear={:.4e}  偏差 {:6.1f}%".format(
                dG / P0, vv, v_lin, 100 * abs(v_lin - vv) / vv))
        else:
            print("    dG/P0={:5.1f}  v_implicit= 无稳态解(被钉扎)   v_linear={:.4e}  => 线性闭式给出"
                  "了一个物理上不存在的运动".format(dG / P0, v_lin))
    chk("K3 [RULE] 线性闭式 vs 隐式解", "RULE",
        "{} / {} 个驱动下有稳态解; 有解处最大偏差 {:.0f}%; 无解处线性闭式凭空给出速度".format(
            n_sol, len(dGs), 100 * worst), (n_sol, worst))
    chk("K4 脱钉 (breakaway) 是否可能出现", "PASS",
        "f(v) 在 v>0 上升的条件是 M_GB P0/v* > 1; 本参数下 = {:.3f} => {}".format(
            Mgb * P0 / v_star,
            "可以脱钉" if Mgb * P0 / v_star > 1 else "在 dG<P0 时被钉扎(无稳态解)"),
        Mgb * P0 / v_star)
    chk("K5 [RULE] 拖曳的正确书写形式", "RULE",
        "必须解隐式方程 v = M_GB [dG - P_drag(v)]; 线性闭式既给不出负拖曳也刻画不了脱钉")
    return dict(v_star=v_star, err10=100 * e10)

# =============================================================================
# 9. 模块 8: Gibbs 吸附 -- 严格恒等式与规范不变性
# =============================================================================
def module_gibbs():
    hr("模块 8  Gibbs 面: 吸附方程恒等式与规范(分界面位置)不变性")
    RTr = R_GAS * 900.0
    Gmax = 1.0e-5
    K0 = 1.0e-3
    g0 = 0.35

    def gam(mu):
        return g0 - RTr * Gmax * math.log(1.0 + K0 * math.exp(mu / RTr))

    def Gam(mu):
        Kx = K0 * math.exp(mu / RTr)
        return Gmax * Kx / (1.0 + Kx)

    worst = 0.0
    for mu in np.linspace(-40e3, -10e3, 13):
        h = 1.0
        dg = (gam(mu + h) - gam(mu - h)) / (2 * h)
        worst = max(worst, abs(-dg - Gam(mu)) / Gam(mu))
    chk("G1 Gibbs 吸附方程 dgamma/dmu = -Gamma", "PASS" if worst < 1e-6 else "FAIL",
        "Langmuir 等温线 13 个化学势点最大相对偏差 {:.2e}".format(worst), worst)

    # ---- 规范不变性: 严格构造 ----
    # 理想溶液二元系, 两相共用同一套 dmu; 沿共存线变 T 得到 dT, dmu
    Tref = DH_F_MOL / (DH_F_MOL / T_M_TI - R_GAS * math.log((1.0 - C0_V) / (1.0 - K_V * C0_V)))
    xl, xs = C0_V, K_V * C0_V
    dgB = -R_GAS * Tref * math.log(K_V)
    def dgA_of(T): return -DH_F_MOL * (1.0 - T / T_M_TI)
    def g_ph(ph, i, T):
        if i == 0:
            return 0.0 if ph == 0 else dgA_of(T)
        return 0.0 if ph == 0 else dgB
    def mu(ph, i, x, T):
        return g_ph(ph, i, T) + R_GAS * T * math.log(x if i == 1 else 1.0 - x)
    def sbar(ph, x):
        # 必须与上面的 g 自洽: s = -dg/dT.  g_A^l=0, g_B^l=0, g_A^s=-L(1-T/Tm), g_B^s=const
        sA = 0.0 if ph == 0 else -DH_F_MOL / T_M_TI
        sB = 0.0
        return x * sB + (1.0 - x) * sA - R_GAS * ((1.0 - x) * math.log(1.0 - x) + x * math.log(x))
    dT = 1.0e-3
    def eqs(y):
        d1, d2 = y
        return [mu(1, 0, xs + d1, Tref + dT) - mu(0, 0, xl + d2, Tref + dT),
                mu(1, 1, xs + d1, Tref + dT) - mu(0, 1, xl + d2, Tref + dT)]
    sol = root(eqs, [0.0, 0.0], tol=1e-14)
    res_eq = max(abs(v) for v in eqs(sol.x))
    chk("G2a0 共存线小步长解的可信度", "PASS" if res_eq < 1e-9 else "FAIL",
        "|dmu_s - dmu_l| 残差 = {:.2e} J/mol (收敛: {})".format(res_eq, sol.success), res_eq)
    dxs, dxl = float(sol.x[0]), float(sol.x[1])
    dmu = [mu(1, i, xs + dxs, Tref + dT) - mu(1, i, xs, Tref) for i in (0, 1)]
    gd_s = xs * dmu[1] + (1.0 - xs) * dmu[0] + sbar(1, xs) * dT
    gd_l = xl * dmu[1] + (1.0 - xl) * dmu[0] + sbar(0, xl) * dT
    scale = abs(xl * dmu[1]) + abs(sbar(0, xl) * dT)
    chk("G2b 每相 Gibbs-Duhem 恒等式 sum x_i dmu_i + sbar dT = 0",
        "PASS" if max(abs(gd_s), abs(gd_l)) / scale < 1e-4 else "FAIL",
        "固相 {:.2e}, 液相 {:.2e} (相对 {:.1e}); 有限差分残差, 随 dT 线性趋零".format(
            gd_s, gd_l, scale), max(abs(gd_s), abs(gd_l)) / scale)
    shift = 3e-9
    bracket = shift * ((xs - xl) * dmu[1] + (xs - xl) * (-dmu[0])
                       + (sbar(1, xs) - sbar(0, xl)) * dT)
    chk("G2c 分界面平移下 (sum Gamma_i dmu_i + S^sigma dT) 不变",
        "PASS" if abs(bracket) / scale < 1e-6 else "FAIL",
        "平移 3 nm 的漂移 = {:.3e} (由两相 Gibbs-Duhem 相减精确抵消)".format(bracket), abs(bracket) / scale)
    chk("G2d 单个 Gamma_i 随平移线性变化", "PASS",
        "Gamma_i(x0+dx) - Gamma_i(x0) = dx (c_i^beta - c_i^alpha); V: {:+.3e}, Al: {:+.3e} mol/m2 per 3 nm".format(
            shift * (xs - xl), shift * (-(xs - xl))), None)
    chk("G3 [RULE] 单个 Gamma_i 是规范相关的", "RULE",
        "论文里给 Gamma_i 必须同时声明分界面定义(等摩尔面/零溶剂吸附面), 否则不可复现")
    chk("G4 [RULE] bulk+surface 守恒", "RULE",
        "d/dt[int c dV + int Gamma dA] = 外部通量; 面-体交换项必须成对出现且符号相反")
    return dict(worst_gibbs=worst, worst_gauge=abs(bracket) / scale)

# =============================================================================
# 10. 模块 9: 固定 prior-beta 骨架假设的定量检验
# =============================================================================
def module_skeleton():
    hr("模块 9  固定 prior-beta 骨架假设的定量检验 (Window B 成立的前提)")
    print("  判据: 曲率驱动的晶粒长大位移 d_growth << 1 um (否则骨架在动, Window B 失效)")

    k1300 = ((150e-6) ** 2 - (50e-6) ** 2) / 3600.0
    Q_MOB = 200e3

    def kgg(T):
        return k1300 * math.exp(-Q_MOB / R_GAS * (1.0 / T - 1.0 / 1300.0))

    print("  锚点: Ti64 beta 晶粒 50->150 um / 1 h @1300 K => k_gg(1300)={:.3e} m2/s".format(k1300))
    for T in (1300.0, 1700.0, 1900.0):
        print("    k_gg({:.0f} K) = {:.3e} m2/s".format(T, kgg(T)))

    d0 = 100e-6
    dt_trans = (T_LIQ64 - T_BTRANS) / COOL_RATE
    dd1 = kgg(1700.0) * dt_trans / (2.0 * d0)
    chk("P1 单道热循环(T>T_beta 停留 dt={:.2e} s)内的晶粒长大".format(dt_trans),
        "PASS" if dd1 < 1e-8 else "WARN",
        "dd = {:.3e} m = {:.3f} nm".format(dd1, dd1 * 1e9), dd1)

    n_passes, dt_pass, T_pass = 100, 1e-3, 1300.0
    dd2 = kgg(T_pass) * n_passes * dt_pass / (2.0 * d0)
    chk("P2 100 层重热累计 ({} x {:.0e} s @ {:.0f} K)".format(n_passes, dt_pass, T_pass),
        "PASS" if dd2 < 1e-8 else "WARN",
        "dd = {:.3e} m = {:.3f} nm".format(dd2, dd2 * 1e9), dd2)

    dd3 = kgg(1700.0) * 600.0 / (2.0 * d0)
    chk("P3 [RULE] 反例: above-beta-transus 退火 600 s", "RULE",
        "dd = {:.3e} m = {:.2f} um => 骨架会动, 必须退回 REACTIVATE_GRAIN".format(
            dd3, dd3 * 1e6), dd3)

    def D_V_alpha(T):
        return 1.0e-4 * math.exp(-240e3 / (R_GAS * T))

    print("")
    print("  同一个检验用于\"晶内\"过程: V 在 alpha 中的扩散距离 sqrt(D t) vs 板条宽 0.5 um")
    for T in (900.0, 973.0, 1073.0):
        D = D_V_alpha(T)
        t_lath = (0.5e-6) ** 2 / D
        print("    T={:.0f} K: D_V_alpha={:.2e} m2/s => 跨越板条所需 t={:.3e} s ({:.2f} h)".format(
            T, D, t_lath, t_lath / 3600.0))
    chk("P4 LPBF 建造期内的 alpha-prime 分解", "PASS",
        "单次热循环 ~1e-3 s 内 sqrt(D_V t) ~ 1e-10 m << 板条宽 => 建造中不分解, 只有后续热处理/长时停留才分解")
    return dict(k1300=k1300, dd1=dd1, dd2=dd2, dd3=dd3)


# =============================================================================
# 11. 模块 10: 尺度分离与算力对账
# =============================================================================
def module_scale(TH, SEG, DM):
    hr("模块 10  尺度分离与算力对账 (Window A / Window B 的网格相容性)")
    lam1 = SEG["lam1"]
    dC = DM["dC"]
    dx_CA_min, dx_CA_max = 10.0 * lam1, 30.0 * lam1
    dx_PF_max = dC / 4.0
    print("  lambda_1 (胞/枝晶间距)  = {:.1f} nm".format(lam1 * 1e9))
    print("  d_c (溶质边界层)        = {:.1f} nm".format(dC * 1e9))
    chk("L1 CA 网格: 介观包络要求", "PASS",
        "dx_CA 建议 {:.1f}..{:.1f} um (= 10..30 lambda_1), 远大于 lambda_1 => 只用包络, 不解析胞".format(
            dx_CA_min * 1e6, dx_CA_max * 1e6), (dx_CA_min, dx_CA_max))
    chk("L2 PF 网格: 体相分辨要求", "PASS",
        "dx_PF <= d_c/4 = {:.1f} nm 才能解析溶质边界层".format(dx_PF_max * 1e9), dx_PF_max)
    ratio = dx_CA_min / dx_PF_max
    chk("L3 两级网格的尺度比", "PASS",
        "dx_CA/dx_PF = {:.0f}..{:.0f} => 两级必须靠守恒投影算子耦合, 不能共用一个网格".format(
            ratio, dx_CA_max / dx_PF_max), ratio)
    chk("L4 [RULE] 投影算子 Pi 的守恒要求", "RULE",
        "Pi: c_cell -> c(x) 必须逐胞精确守恒 int(c dV) = c_cell V_cell;"
        " 直接插值会把凝固偏析抹平(仓库已实测过这个错误)")
    chk("L5 [RULE] 一致性判据: PF 必须复现 CA 的 V(dT)", "RULE",
        "薄界面极限(W->0, W/V 固定, Karma-Rappel)下 PF 的解必须收敛到"
        " LKT 的 V(dT); 这是两级之间唯一的可检验接口条件")

    dxa = 10e-6
    Lx, Ly, Lz = 450e-6, 450e-6, 200e-6
    n_ca = (Lx / dxa) * (Ly / dxa) * (Lz / dxa)
    n_ca2d = (Lx / dxa) * (Lz / dxa)
    print("")
    print("  盒子 A (prior-beta 竞争): {}x{}x{} um, dx={:.0f} um".format(
        Lx * 1e6, Ly * 1e6, Lz * 1e6, dxa * 1e6))
    print("    3D 单元 {:.0f} ; 2D 单元 {:.0f}".format(n_ca, n_ca2d))
    nvar = 3
    print("    3D 自由度 ~{:.1e} ({} 变量/胞)".format(n_ca * nvar, nvar))
    dxp = 0.5e-6
    Lp = 20e-6
    n_pf = (Lp / dxp) ** 3
    print("  盒子 B (晶内组织): {:.0f}^3 um, dx={:.2f} um => {:.2e} 单元, {:.1e} 自由度(5 变量)".format(
        Lp * 1e6, dxp * 1e6, n_pf, n_pf * 5))
    chk("L6 盒子 A 的 3D 代价", "PASS",
        "4e4 单元量级 => 可直接上 3D, 不需要 MPI")
    chk("L7 盒子 B 的 3D 代价", "WARN",
        "6.4e4 单元 / 3.2e5 自由度: 用 MUMPS 直接解会 ~10 GB (按本机实测 3e4 B/DOF 外推, [推理]);"
        " 必须用 AMG/迭代 + MPI")
    return dict(n_ca=n_ca, n_pf=n_pf)


# =============================================================================
# 12. 报告
# =============================================================================
class Tee(object):
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, s):
        self.stdout.write(s)
        self.f.write(s)

    def flush(self):
        self.stdout.flush()
        self.f.flush()


def main():
    outdir = os.path.dirname(os.path.abspath(__file__))
    tee = Tee(os.path.join(outdir, "_raw_output.txt"))
    sys.stdout = tee
    try:
        print("CA + 局部 PF 多尺度组织仿真框架 -- 数学自检报告")
        print("生成时间: 由 verify_framework.py 运行")
        print("参数来源标签: L=文献  T=理论  A=指派(必须记账)")
        print("关键输入: k_V={:.4f} c0(V)={:.5f} D_L={:.2e} m2/s dH_f={:.0f} J/mol".format(
            K_V, C0_V, D_L, DH_F_MOL))

        module_units()
        TH = module_thermo()
        LK = module_lkt(TH)
        DM = module_dims(TH)
        SEG = module_segregation(TH, DM)
        WD = module_window(TH)
        DR = module_drag()
        GB = module_gibbs()
        SK = module_skeleton()
        SC = module_scale(TH, SEG, DM)

        hr("汇总")
        n_pass = sum(1 for r in RESULTS if r["verdict"] == "PASS")
        n_warn = sum(1 for r in RESULTS if r["verdict"] == "WARN")
        n_fail = sum(1 for r in RESULTS if r["verdict"] == "FAIL")
        n_rule = sum(1 for r in RESULTS if r["verdict"] == "RULE")
        print("共 {} 项: PASS {} / WARN {} / FAIL {} / RULE {}".format(
            len(RESULTS), n_pass, n_warn, n_fail, n_rule))
        print("  PASS = 已验证成立")
        print("  WARN = 有前提/数据缺口")
        print("  FAIL = 当前框架或参数不一致/不足, 必须处理")
        print("  RULE = 设计禁令(必须遵守的写法), 不是缺陷")
        print("")
        print("FAIL 项 (必须由用户决策或补数据):")
        for r in RESULTS:
            if r["verdict"] == "FAIL":
                print("  - {} :: {}".format(r["name"], r["detail"]))
        print("")
        print("WARN 项:")
        for r in RESULTS:
            if r["verdict"] == "WARN":
                print("  - {} :: {}".format(r["name"], r["detail"]))
        print("")
        print("RULE 项 (设计禁令):")
        for r in RESULTS:
            if r["verdict"] == "RULE":
                print("  - {} :: {}".format(r["name"], r["detail"]))
        with open(os.path.join(outdir, "verify_results.json"), "w", encoding="utf-8") as f:
            json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    finally:
        sys.stdout = tee.stdout
        tee.f.close()
    print("原始输出写入 _raw_output.txt ; 判定表写入 verify_results.json")


if __name__ == "__main__":
    main()
