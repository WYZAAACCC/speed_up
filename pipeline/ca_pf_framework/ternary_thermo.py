#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ternary_thermo.py --- Ti-Al-V 三元（Al+V 双溶质）热力学闭合：单一参数来源。

为什么需要这个文件（对 MATH_FRAMEWORK.md 的兼容性修复）
============================================================================
MATH_FRAMEWORK.md §5.1 的状态量本来就写成 c_i (i in {V,Al})、Gamma_i、M^c_ij
（向量/矩阵写法 => 兼容）。但**真正定数值的三处闭合还是标量**：

  * §5.2 的两相化学势等式只解了 1 个溶质 + 溶剂（2 方程 2 未知 => 一对离散的
    (c_s, c_l)，并且 §5.2 由此断言"热力学输入只有两个独立参数 (k, dH_f, T_m)"）；
  * ca3d.py 的 C0_V、K_V 是标量；alloy_pf_std.py 的 c 是标量；
  * gibbs_physics.py 的 McLean 等温线只对一个物种；windowB_surface.py 只有单个 Gam。

三元（3 组分 = Ti + Al + V）在固定 T 下的两相区**不是一对点**：相律
F = C - P + 2 = 3，固定 T、P 后 F = 1 => 系线是**一条曲线（1 参数族）**。
所以标量闭合必须显式降级为"准二元子集"，并补上三元闭合。

本模块给出并实现的三元闭合（**已在 _chk_ternary.py 有数值判据**）
============================================================================

符号
----
  * c_i：摩尔分数（atom fraction），i in {Al, V}；溶剂 Ti：X = 1 - c_Al - c_V
  * 自由能按"每摩尔原子"记 gt [J/mol]，体自由能密度 f = gt / V_m
  * **符号约定（关键，本仓库推错过一次）**：dg_i = g_i^sol - g_i^liq
      - 溶剂 Ti 锚：dg_Ti(T) = -dH_f (1 - T/T_m)
        （T < T_m 时 dg_Ti < 0 <=> 固相更稳；T_m 处为 0）
      - 逐溶质：dg_i(T) = dH_i - T dS_i（**每溶质两个数**，见下）

R0. 理想置换溶液（可叠加正规溶液相互作用）
        gt_phi(c) = Sum_j c_j g_j^phi + R T Sum_j c_j ln c_j + E^phi(c)
        E^phi(c)  = Sum_{j<k} L_jk^phi c_j c_k            （可选项，默认 0）
    => 化学势**精确**为
        mu_i^phi  = g_i^phi  + R T ln c_i^phi + Sum_{k != i} L_ik^phi c_k^phi - E^phi
        mu_Ti^phi = g_Ti^phi + R T ln X^phi   + Sum_{k != Ti} L_Ti,k^phi c_k^phi - E^phi
    （理想部分 mu_i = g_i + RT ln c_i，**没有 X 比**；这是置换式理想溶液的精确结果）
    推导（(C-1) 个独立组分，求和跑遍**全部** C 个组分）：
        G = n gt(c),  mu_i = gt + d gt/d c_i - Sum_j c_j d gt/d c_j
        d gt/d c_i = g_i + RT(ln c_i + 1) + dE/dc_i
        Sum_j c_j d gt/dc_j = (gt - E) + RT + 2E          （E 对全部组分 2 次齐次）
      => mu_i = g_i + RT ln c_i + dE/dc_i - E             （RT 项抵消）
    ⚠ 本模块曾把 -E 误写成 -2E（判据 T-A5b 抓到）；L = 0 时两者同（E=0），
      所以理想部分的全部结论不受影响。

R1. 系线族（逐溶质分配）
        c_i^sol = k_i(T) c_i^liq,   k_i(T) = exp[ -dg_i(T) / (R T) ]
    **三元下仍然逐溶质成立**，但**系线不是一对点**：给定 c^liq，c^sol 被唯一确定，
    而 c^liq 自身在固定 T 下只能沿一条曲线走（相律 F=1）。

R2. 液相线恒等式（**新**；把两溶质绑在一起的那条约束）
    固相成分必须是一个合法成分，即分数组分和为 1：
        G(T; c^liq) := Sum_i k_i(T) c_i^liq + k_Ti(T) X^liq = 1            (★)
      * G 就是"按 k 逐组分放大后固相的总和"，所以 (★) 的含义是
        **"这个液相成分恰好能被放大成一个合法固相"**；
      * 纯 Ti 检验：c^liq = 0 => G = k_Ti = 1 只在 T = T_m 成立 => 纯 Ti 液相线 = T_m；
      * **液相线**：把 c^liq = c0（合金名义成分）代入 (★) 解 T；
      * **固相线**：把 c_i^liq = c_i^0 / k_i(T) 代入 (★) 解 T；
      * **凝固区间** dT_0 = T_L - T_S 于是成为**预测值**（可对文献 45-50 K 检验）；
      * (★) 是**一条**方程 => k_Al 与 k_V **不能自由各选**：给定液相线温度
        （Ti64 文献 ~1923 K）与其中一个，另一个被唯一确定（见 _chk_ternary.py T-A7）。

R3. 分配**矩阵**（不是标量）
        k_ij := d c_i^sol / d c_j^liq （固定 T，沿系线族）
      理想置换溶液（L = 0）=> k_ij = k_i delta_ij（**精确对角**，无交叉耦合）；
      含 L_jk != 0 时出现非对角项，量级 O(L/RT)。
      => 想要非零交叉分配，必须由 CALPHAD 给相互作用参数；不能凭空造。

R4. 抗截留 / 拖曳的向量化
      抗截留通量逐溶质各带一项：j_at,i ~ a_t W (c_i^l0 - c_i^s0) d_t phi / |grad phi|；
      溶剂项由 Sum_i c_i = 1 隐含（j_at,Ti = -Sum_i j_at,i）。
      二元退化时**逐位**回到 alloy_pf_std.py 现在用的那一项（判据 T-A10）。

R5. 独立输入计数（替代 §5.2 的"只有两个独立参数"）
      * 溶剂 Ti：dH_f、T_m（已知，14150 J/mol、1941 K）
      * 每溶质：dH_i、dS_i => 合计 4 个未知
      * (★) 提供 1 条约束（用文献液相线闭合）=> **3 个自由参数**
      => 三元下"只有两个独立参数"**不成立**；§5.2 必须降级为准二元子集。

记账
----
[L] 文献直读 | [T] 本仓库推导 | [A] 指派/标定（论文必须标注）
本模块**不引入任何未标记的数**。
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq

# ---------------------------------------------------------------------------
# 常数（与 alloy_pf_std.py / pf1d_moose 的生产仪器同源）
# ---------------------------------------------------------------------------
R = 8.314462618          # J/mol/K                      [L] 定义值
V_M = 1.1345e-5          # m^3/mol  生产仪器口径          [L] pf1d_moose 常数
DHF_TI = 14150.0         # J/mol    纯 Ti 熔化焓          [L]
TM_TI = 1941.0           # K        纯 Ti 熔点            [L]

# Ti64 名义成分（mol frac）—— [T] 由 wt% 换算，见 verify_framework.mole_fracs
X_AL_TI64 = 0.1020
X_V_TI64 = 0.0360
T_LIQ_TI64 = 1923.0      # K  Ti-6Al-4V 液相线（文献 1920-1928 K）  [L] 见 audit §4

# 生产仪器里被当成"唯一溶质"的那个数：k = 0.6303 是从 f_loc 的 A_part 反解出来的
# （CALPHAD_REQUEST.md 已注明"不是从相图取的"）。三元年审时它只能被解释成
# **某一**溶质在**某一**相变里的分配系数，不能再当成"V 在 L->beta 的分配系数"。
K_LEGACY = 0.6303        # [A] 反解值，非相图值


class TernaryClosure:
    """Ti-(Al,V) 三元闭合，相 = (liq, sol)。

    Parameters
    ----------
    solutes : dict[str, (float, float)]
        {name: (dH_i, dS_i)}，dg_i(T) = dH_i - T dS_i（sol - liq）[J/mol, J/mol/K]。
    dHf, Tm : 纯 Ti 熔化焓/熔点（溶剂锚）。
    Lliq, Lsol : dict[(str,str), float]
        正规溶液相互作用参数 L_jk^phi [J/mol]；键为组分对，例如 ('Al','V')。
    """

    def __init__(self, solutes, dHf=DHF_TI, Tm=TM_TI, Lliq=None, Lsol=None):
        if not solutes:
            raise ValueError("至少给一个溶质")
        self.names = list(solutes)
        self.params = {k: (float(v[0]), float(v[1])) for k, v in solutes.items()}
        self.dHf = float(dHf)
        self.Tm = float(Tm)
        self.Lliq = dict(Lliq or {})
        self.Lsol = dict(Lsol or {})

    # ---------------- 标准态差与分配系数 ----------------
    def dg_Ti(self, T):
        """dg_Ti(T) = g_Ti^sol - g_Ti^liq = -dHf (1 - T/Tm)   [T]"""
        return -self.dHf * (1.0 - T / self.Tm)

    def dg_i(self, name, T):
        dH, dS = self.params[name]
        return dH - T * dS

    def k_Ti(self, T):
        return math.exp(-self.dg_Ti(T) / (R * T))

    def k(self, T):
        return {n: math.exp(-self.dg_i(n, T) / (R * T)) for n in self.names}

    def lnk_of_T(self, T):
        """{name: ln k}；线性于 1/T：ln k = -dH/(RT) + dS/R。"""
        return {n: self.params[n][1] / R - self.params[n][0] / (R * T)
                for n in self.names}

    def dH(self, name):
        return self.params[name][0]

    def dS(self, name):
        return self.params[name][1]

    # ---------------- 系线 ----------------
    def tie_solid(self, cL, T):
        """c_i^sol = k_i(T) c_i^liq（R1）。返回 dict。"""
        k = self.k(T)
        return {n: k[n] * cL[n] for n in self.names}

    def G(self, T, cL):
        """R2 的 (★) 左端减 1：G(T;cL) - 1。G=1 <=> 系线存在（液相线上）。"""
        k = self.k(T)
        s = sum(k[n] * cL[n] for n in self.names)
        X = 1.0 - sum(cL.values())
        return s + self.k_Ti(T) * X - 1.0

    def _scan_roots(self, f, Tlo, Thi, n=4001, xtol=1e-10):
        """在 [Tlo,Thi] 上找 f 的全部根（含 f 恰好等于 0 的格点）。

        注意：纯 Ti 极限下 G(T) = k_Ti(T) - 1 在 T = T_m 处**恰好为 0**（不是变号），
        所以必须显式处理零格点，否则会漏掉液相线（判据 T-A4）。
        """
        Tg = np.linspace(Tlo, Thi, n)
        fv = np.array([f(float(t)) for t in Tg])
        roots = []
        zero = np.where(fv == 0.0)[0]
        for i in zero:
            roots.append(float(Tg[i]))
        sgn = np.sign(fv)
        for i in np.where(sgn[:-1] * sgn[1:] < 0)[0]:
            roots.append(brentq(f, Tg[i], Tg[i + 1], xtol=xtol))
        return roots

    def liquidus(self, c0, Tlo=1600.0, Thi=None, xtol=1e-10):
        """液相线温度：解 G(T; c0) = 1  [T]。"""
        Thi = self.Tm + 200.0 if Thi is None else Thi
        roots = self._scan_roots(lambda T: self.G(T, c0), Tlo, Thi, xtol=xtol)
        if not roots:
            raise RuntimeError("液相线无解：检查 dH_i/dS_i（G 在 [%g,%g] 不在 1 处变号）"
                               % (Tlo, Thi))
        return float(max(roots))   # 高温那一支才是液相线

    def solidus(self, c0, Tlo=1400.0, Thi=None, xtol=1e-10):
        """固相线温度：把 c_i^liq = c_i^0 / k_i(T) 代入 (★) 解 T。"""
        Thi = self.Tm + 200.0 if Thi is None else Thi

        def f(T):
            k = self.k(T)
            cL = {n: c0[n] / k[n] for n in self.names}
            s = sum(k[n] * cL[n] for n in self.names)
            X = 1.0 - sum(cL.values())
            return s + self.k_Ti(T) * X - 1.0

        roots = self._scan_roots(f, Tlo, Thi, xtol=xtol)
        if not roots:
            raise RuntimeError("固相线无解")
        return float(min(roots))   # 低温那一支才是固相线

    def freezing_range(self, c0):
        TL = self.liquidus(c0)
        TS = self.solidus(c0)
        return TL, TS, TL - TS

    # ---------------- 化学势（含相互作用） ----------------
    def _excess(self, phase, c):
        L = self.Lsol if phase == "sol" else self.Lliq
        if not L:
            return 0.0
        full = dict(c)
        full["Ti"] = 1.0 - sum(c.values())
        E = 0.0
        for (a, b), v in L.items():
            E += v * full[a] * full[b]
        return E

    def mu(self, phase, c, T):
        """mu_i^phi（J/mol）。phase in {'liq','sol'}；c 为 {name: c_i}（不含 Ti）。"""
        g = self._g(phase, T)
        L = self.Lsol if phase == "sol" else self.Lliq
        E = self._excess(phase, c)
        full = dict(c)
        full["Ti"] = 1.0 - sum(c.values())
        out = {}
        for n in self.names:
            ex = 0.0
            for (a, b), v in L.items():
                if a == n:
                    ex += v * full[b]
                elif b == n:
                    ex += v * full[a]
            out[n] = g[n] + R * T * math.log(max(c[n], 1e-300)) + ex - E
        exTi = 0.0
        for (a, b), v in L.items():
            if a == "Ti":
                exTi += v * full[b]
            elif b == "Ti":
                exTi += v * full[a]
        out["Ti"] = (g["Ti"] + R * T * math.log(max(full["Ti"], 1e-300))
                     + exTi - E)
        return out

    def _g(self, phase, T):
        """标准态化学势 g_j^phi（相对约定：g_Ti^liq = 0, g_i^liq = 0）。"""
        out = {"Ti": 0.0 if phase == "liq" else self.dg_Ti(T)}
        for n in self.names:
            out[n] = 0.0 if phase == "liq" else self.dg_i(n, T)
        return out

    # ---------------- 数值独立复核（不依赖 R1 的解析式） ----------------
    def solve_tie_numeric(self, T, cL, x0=None):
        """独立解 mu_i^sol = mu_i^liq (i = Al, V, Ti) 求 c^sol（不用 R1）。

        3 个残差、2 个未知（c_Al^sol, c_V^sol）做最小二乘；
        理想溶液下残差应到机器精度（R1 的解析式满足全部 3 个等式）。
        """
        from scipy.optimize import least_squares

        def res(y):
            cS = {n: float(y[j]) for j, n in enumerate(self.names)}
            mL = self.mu("liq", cL, T)
            mS = self.mu("sol", cS, T)
            return [mS[n] - mL[n] for n in list(self.names) + ["Ti"]]

        y0 = np.array(x0 if x0 is not None
                      else [self.k(T)[n] * cL[n] for n in self.names])
        sol = least_squares(res, y0, xtol=1e-15, ftol=1e-15, gtol=1e-15)
        cS = {n: float(sol.x[j]) for j, n in enumerate(self.names)}
        return cS, float(np.max(np.abs(sol.fun)))

    def partition_matrix(self, T, cL, h=1e-7):
        """k_ij = d c_i^sol / d c_j^liq（固定 T，沿系线族）。R3。

        理想溶液 => 精确对角（解析）。含 L != 0 时应由 mu 等式给出非对角项：
        这里用 solve_tie_numeric 的数值 Jacobian 来覆盖（默认 L=0 时与解析一致）。
        """
        k = self.k(T)
        if not (self.Lliq or self.Lsol):
            K = np.zeros((len(self.names), len(self.names)))
            for i, a in enumerate(self.names):
                for j, b in enumerate(self.names):
                    K[i, j] = k[a] if a == b else 0.0
            return K
        K = np.zeros((len(self.names), len(self.names)))
        for j, nj in enumerate(self.names):
            for sign in (+1.0, -1.0):
                cLp = dict(cL)
                cLp[nj] = cL[nj] + sign * h
                cSp, _ = self.solve_tie_numeric(T, cLp)
                for i, ni in enumerate(self.names):
                    K[i, j] += sign * cSp[ni] / (2.0 * h)
        return K

    # ---------------- 便利构造器 ----------------
    @classmethod
    def from_k_at_T(cls, k_at_T, Tref, Tm=TM_TI, dH=None, dS=None, **kw):
        """由"某温度下的 k 值"造闭合。

        k_at_T = {name: k}。每个溶质给 dH_i（或 dS_i）之一即可：
          ln k = -dH/(R T) + dS/R => 给定 dH_i 反解 dS_i，或反之。
        未提供的那个必须由调用者显式传入（否则欠定 —— 这正是 R5 的记账点）。
        """
        dH = dict(dH or {})
        dS = dict(dS or {})
        sol = {}
        for n, kk in k_at_T.items():
            if n not in dH and n not in dS:
                raise ValueError("溶质 %s：必须给 dH 或 dS 之一（否则欠定）" % n)
            if n in dH:
                dHi = dH[n]
                dSi = R * (math.log(kk) + dHi / (R * Tref))
            else:
                dSi = dS[n]
                dHi = R * Tref * (math.log(kk) + dSi / R)
            sol[n] = (dHi, dSi)
        return cls(sol, Tm=Tm, **kw)


# ---------------------------------------------------------------------------
# 二元退化（与 MATH_FRAMEWORK.md §5.2 逐位对账用）
# ---------------------------------------------------------------------------
def binary_T_pair(c_l, c_s, dHf=DHF_TI, Tm=TM_TI):
    """§5.2 的 T_pair：给定系线对，反求温度 [T]。

        RT ln[(1-c_s)/(1-c_l)] = dHf (1 - T/Tm)
    <=> T = dHf / ( dHf/Tm + R ln[(1-c_s)/(1-c_l)] )
    （与 §5.2 写的 dHf/(dHf/Tm - R ln[(1-c_l)/(1-c_s)]) 恒等，因为负号翻过来。）
    """
    Xs, Xl = 1.0 - c_s, 1.0 - c_l
    return dHf / (dHf / Tm + R * math.log(Xs / Xl))


def binary_k_A(T, dHf=DHF_TI, Tm=TM_TI):
    """溶剂（Ti）的分配系数 k_A = exp(-dg_A/(RT))，dg_A = -dHf(1-T/Tm)。"""
    dgA = -dHf * (1.0 - T / Tm)
    return math.exp(-dgA / (R * T))
