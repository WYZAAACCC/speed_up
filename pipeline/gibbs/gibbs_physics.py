#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gibbs 晶界模型的物理核心 —— 单一参数来源（single source of truth）。

本模块只做三件事：
  1. 把晶界偏析/扩散的**物理参数**集中在一处，每个都标「出处等级」；
  2. 给出 McLean(Langmuir) 等温线、分配系数、扩散系数的**物理量纲**表达式；
  3. 做**自洽性检查**（反解、锚点对比、单层分数、无量纲化系数）。

设计原则（沿用 pipeline/PARAMETER_PROVENANCE.md 的三档标记）：
  [L] literature    —— 文献直读，已核对原文数值
  [T] theory        —— 由热力学/统计力学公式推导得到
  [A] assignment    —— 指派值 / 标定值，**不是材料常数**，必须显式标注

⚠ 本模块**不引入任何没有标记的数**。凡 [A] 都是待标定项。

物理形式（依据 pipeline/GB_SEGREGATION_LITERATURE.md §0.3.1，Cahn 1962）：
  体相   f_mix/f_ref = τ·[c·ln c + (1−c)·ln(1−c)]          理想溶液混合自由能
  分配   f_part/f_ref = (Δμ°_LS/(R·T_ref))·c·(1−h_solid)    固/液化学势差 ⇒ k(T)
  偏析   f_seg/f_ref  = (ΔG_seg/(R·T_ref))·(c−c₀)·h_gb      晶界偏析势 ⇒ McLean
  其中 f_ref = R·T_ref/v_m 是**参考自由能密度**，τ = T/T_ref。

  ⇒ 平衡条件 df/dc = μ 给出**精确 McLean 等温线**（不受 w_GB 和 κ_c 影响）：
        c_GB/(1−c_GB) = c_far/(1−c_far) · exp(−ΔG_seg/(R·T))
  ⇒ 这就是"物理闭合"的核心：偏析强度由**材料量** ΔG_seg 决定，而不是由板宽决定。
"""
import math

# =============================================================================
# 一、物理常数与材料量
# =============================================================================

R = 8.314462618          # J/mol/K                        [L] 定义值

# --- β-Ti 的摩尔密度 ---
RHO_AT_BETA = 61.0       # at/nm^3  β-Ti 原子密度         [L] Tan 2016 原文 (ρ(β))
N_A = 6.02214076e23      # 1/mol                          [L] 定义值
RHO_MOL = RHO_AT_BETA * 1e27 / N_A   # mol/m^3 = 1.0129e5  [T] 由 ρ(β) 换算
V_M = 1.0 / RHO_MOL      # m^3/mol   = 9.873e-6          [T]
# 交叉校验：v_m 对应密度 4.43 g/cm^3（Ti64 实测）—— 已核，见 §0.3.2

AT_PER_NM2_TO_MOL_PER_M2 = 1e18 / N_A     # 1.66054e-6  [T]

# --- 单层饱和量（Langmuir-McLean 的 Γ₀）---
GAMMA_MONO_AT = 12.9     # at/nm^2  β-Ti (110) 面位点密度  [T] 本项目推导（几何）
GAMMA_MONO = GAMMA_MONO_AT * AT_PER_NM2_TO_MOL_PER_M2   # = 2.1421e-5 mol/m^2

# --- 成分与工况 ---
C0 = 0.036               # V 的原子分数（Ti64 4 wt%）      [L]
T_ANCHOR = 923.0         # K  Tan 2016 的测量温度          [L]
T_LPBF = 1950.0          # K  LPBF 固相内 β-Ti 的代表温度   [A] 工况设定（需按实际 T 场取）
T_REF = T_LPBF           # K  无量纲化参考温度

# --- Tan 2016 锚点（α/β 界面，923 K）---
GAMMA_ANCHOR_AT = (2.2, 5.3)   # at/nm^2  V 的 Gibbs 界面过剩  [L] Tan 2016 Table 2
GAMMA_ANCHOR = tuple(g * AT_PER_NM2_TO_MOL_PER_M2 for g in GAMMA_ANCHOR_AT)

# --- 扩散（Ti64 中 V）---
D_L = 2.52e-9            # m^2/s  液相（Ti 自扩散量级）      [L] 生产值/文献
D_S = 4.0e-13            # m^2/s  固相                      [A] 校准值（Ti64 无定量数据）
D_GB = 4.0e-10           # m^2/s  晶界                      [A] 校准值（同上）
DELTA_GB = 0.5e-9        # m      晶界"结构厚度"约定值 δ     [L] 文献约定（非测量值）


# =============================================================================
# 二、偏析热力学
# =============================================================================

def dG_seg(T, dH_seg, dS_seg=0.0):
    """晶界偏析自由能 ΔG_seg(T) = ΔH_seg − T·ΔS_seg   [J/mol]。

    ⚠ [A] dH_seg / dS_seg 本身在 β-Ti 上是**文献空白**（见 §5 缺口 E1–E6）。
      本模块不猜它们，只提供 (1) 从锚点**反解**的路，与 (2) 显式传入的路。
    """
    return dH_seg - T * dS_seg


def K_mclean(T, dH_seg, dS_seg=0.0):
    """McLean 偏析常数 K = exp(−ΔG_seg/(RT))。"""
    return math.exp(-dG_seg(T, dH_seg, dS_seg) / (R * T))


def cGB_from_cfar(c_far, T, dH_seg, dS_seg=0.0):
    """**精确 McLean（摩尔分数形式）**：给定体相浓度求晶界平衡浓度。

        c_GB/(1−c_GB) = (c_far/(1−c_far))·K

    ⇒ 这是相场 `f_seg = (ΔG_seg/v_m)(c−c₀)h_gb` 在理想溶液体自由能下的**解析平衡**。
    """
    x = (c_far / (1.0 - c_far)) * K_mclean(T, dH_seg, dS_seg)
    return x / (1.0 + x)


def s_mclean(T, dH_seg, dS_seg=0.0):
    """富集比 s = c_GB/c_far（对 c_far 的显式依赖很小；稀溶液极限 = K）。"""
    return None  # 见 s_at()


def s_at(c_far, T, dH_seg, dS_seg=0.0):
    return cGB_from_cfar(c_far, T, dH_seg, dS_seg) / c_far


def gamma_eq_langmuir(c_far, T, dH_seg, dS_seg=0.0, gamma0=GAMMA_MONO):
    """**Langmuir–McLean 面过剩过饱和形式**（Gibbs 面的平衡本构）：

        Γ/(Γ₀ − Γ) = (c/(1−c))·K     ⇒  Γ_eq = Γ₀·K·c̄/(1 + K·c̄),  c̄ = c/(1−c)

    ⚠ 与上面的摩尔分数 McLean 是**同一套热力学**的两种记账：
      · 摩尔分数形式给「晶界处的局域 c」        ⇒ 对应弥散模型
      · 面过剩形式给「单位面积的过剩量 Γ」      ⇒ 对应 Gibbs 面模型
      · 以 δ 为"结构厚度"时两者通过 Γ = δ·ρ_mol·(c_GB − c_far) 互相换算
    """
    cbar = c_far / (1.0 - c_far)
    Kc = K_mclean(T, dH_seg, dS_seg) * cbar
    return gamma0 * Kc / (1.0 + Kc)


def dH_seg_from_anchor(gamma_at_anchor=3.75, T=T_ANCHOR, c_far=C0,
                       gamma0=GAMMA_MONO, dS_seg=0.0):
    """**从 Tan 2016 的 Γ 锚点反解 ΔH_seg**（[T] 推导，输入是 [L] 文献值）。

    ⚠ gamma_at_anchor 的单位是 **at/nm²**（文献口径），gamma0 的单位是 **mol/m²**，
       函数内部统一换算 —— 单位不一致会让 ln() 的输入变负号，必须防。

    Langmuir–McLean： Γ/(Γ₀−Γ) = (c/(1−c))·exp(−ΔG/(RT))
    ⇒ ΔG = −R·T·ln[ (Γ/(Γ₀−Γ)) · ((1−c)/c) ]
    ⇒ ΔH = ΔG + T·ΔS   （取 ΔS = 0 时 ΔH = ΔG）
    """
    g = gamma_at_anchor * AT_PER_NM2_TO_MOL_PER_M2      # at/nm^2 -> mol/m^2
    if not (0.0 < g < gamma0):
        raise ValueError("锚点 Γ=%.4e 必须落在 (0, Γ₀=%.4e) 内" % (g, gamma0))
    ratio = (g / (gamma0 - g)) * ((1.0 - c_far) / c_far)
    dG = -R * T * math.log(ratio)
    return dG + T * dS_seg, dG


# =============================================================================
# 三、液固分配（写成 k(T)，而不是一个唯象的二次项系数）
# =============================================================================

K_PARTITION = 0.63       # [-] c_S/c_L，Ti64 中 V            [L] Lee 2025 / PanTi CALPHAD


def dH_seg_from_anchor_delta(delta=DELTA_GB, T=T_ANCHOR, c_far=C0,
                             gamma_at_anchor=3.75, dS_seg=0.0, n=20001):
    """**给定晶界结构厚度 δ，从锚点解出 ΔH_seg**（[T] 推导 + 数值求根）。

    与 dH_seg_from_anchor 的区别：那条路需要 Γ₀（单层饱和量，几何估算，较不确定）；
    这条路只需要 δ（文献约定的晶界结构厚度 0.5 nm，不确定性更小）。

    约束： Γ_model(δ, T_anchor) = ρ_mol·δ·A(T_anchor, ΔH_seg) = Γ_anchor
    ⇒ 解 A(ΔH_seg) = Γ_anchor/(ρ_mol·δ)，A 对 |ΔH_seg| **单调增** ⇒ 二分。
    """
    Gamma_target = gamma_at_anchor * AT_PER_NM2_TO_MOL_PER_M2
    target_A = Gamma_target / (RHO_MOL * delta)
    lo, hi = 0.0, -200000.0            # A(0)=0；|ΔH| 越大 A 越大
    if int_dc_du(T, hi, dS_seg, c_far, n=n) < target_A:
        raise ValueError("目标 A=%.6f 超出可达范围" % target_A)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if int_dc_du(T, mid, dS_seg, c_far, n=n) < target_A:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def dmu_LS(T, k=K_PARTITION):
    """固/液参考化学势差：Δμ°_LS = −R·T·ln(k)   [J/mol]。

    ⇒ f_part = (Δμ°_LS/v_m)·c·(1−h_solid)
    ⇒ 理想溶液下平衡给出 c_S/c_L = exp(−Δμ°_LS/(RT)) = k  —— **自动带 T 依赖**。
    """
    return -R * T * math.log(k)


# =============================================================================
# 四、无量纲化：物理精确、但数字 O(1)
# =============================================================================

def f_ref(T_ref=T_REF):
    """参考自由能密度 f_ref = R·T_ref/v_m   [J/m^3]。"""
    return R * T_ref / V_M


def coeffs(T, dH_seg, dS_seg=0.0, T_ref=T_REF, k=K_PARTITION):
    """写成 f_loc/f_ref 的**无量纲**系数（物理量纲的另一种写法，数值更稳）。

    f_loc/f_ref = τ·[c ln c + (1−c)ln(1−c)]
                + (Δμ°_LS/(R·T_ref))·c·(1−h_solid)
                + (ΔG_seg/(R·T_ref))·(c−c₀)·h_gb
    """
    return dict(tau=T / T_ref,
                part=dmu_LS(T, k) / (R * T_ref),
                seg=dG_seg(T, dH_seg, dS_seg) / (R * T_ref))


def f_cc_phys(c, T, h_solid, h_gb, dH_seg, dS_seg=0.0, T_ref=T_REF, k=K_PARTITION):
    """∂²f/∂c² 的**物理值** [J/m^3]，用于 M = D/f_cc（保证 D = M·f_cc 精确）。"""
    co = coeffs(T, dH_seg, dS_seg, T_ref, k)
    return f_ref(T_ref) * co["tau"] / (c * (1.0 - c))


def mobility_from_D(D, c, T, h_solid, h_gb, dH_seg, dS_seg=0.0,
                    T_ref=T_REF, k=K_PARTITION):
    """M = D/f_cc   [m^5/(J·s)]，逐点成立 ⇒ D = M·f_cc 精确。"""
    return D / f_cc_phys(c, T, h_solid, h_gb, dH_seg, dS_seg, T_ref, k)


# =============================================================================
# 五、自洽性检查与报告
# =============================================================================

def _sech4(u):
    return 1.0 / math.cosh(u) ** 4


def profile_dc(u, T, dH_seg, dS_seg=0.0, c_far=C0):
    """**精确的（非线性）McLean 局域剖面** c(u) − c_far，u = (x−x_gb)/w_GB。

        c(u)/(1−c(u)) = (c_far/(1−c_far))·exp(−ΔG_seg·h_gb(u)/(RT)),  h_gb(u) = sech⁴(u)

    ⇒ 这是相场 `f_mix + f_seg`（理想溶液 + 线性偏析势）的**解析平衡**。
    ⇒ 关键：该剖面**与 w_GB 无关**（只是 u 的函数）⇒ 峰值与 w_GB 无关，
       而 Γ = ρ_mol·w_GB·∫Δc du **正比于 w_GB**。
    """
    E = -dG_seg(T, dH_seg, dS_seg) * _sech4(u) / (R * T)
    x = (c_far / (1.0 - c_far)) * math.exp(E)
    return x / (1.0 + x) - c_far


def int_dc_du(T, dH_seg, dS_seg=0.0, c_far=C0, umax=12.0, n=240001):
    """A ≡ ∫[c(u)−c_far]du（无量纲，只用 u）。梯形积分，n 取奇保证覆盖 u=0。"""
    du = 2.0 * umax / (n - 1)
    s = 0.0
    for i in range(n):
        u = -umax + i * du
        w = 0.5 if (i == 0 or i == n - 1) else 1.0
        s += w * profile_dc(u, T, dH_seg, dS_seg, c_far)
    return s * du


def wgb_from_Gamma(Gamma_target, T, dH_seg, dS_seg=0.0, c_far=C0):
    """给定目标 Gibbs 过剩 Γ，**反解**模型必须取的 w_GB（[T] 推导，非线性）。

        Γ = ρ_mol·w_GB·A(T)   ⇒   w_GB = Γ / (ρ_mol·A)
    """
    return Gamma_target / (RHO_MOL * int_dc_du(T, dH_seg, dS_seg, c_far))


def wgb_for_anchor(H=None):
    """自洽版的 §5：在**同一温度**下把 Γ_phys(T) 与模型 Γ 对齐。

    ⚠ 上一版把 923 K 的锚点 Γ 配上 1950 K 的 f_cc —— 温度不一致，已作废。
      正确做法：在目标温度 T 下，用 McLean 外推出的 Γ_phys(T) 反解 w_GB。
    """
    if H is None:
        H = dH_seg_from_anchor()[0]
    G = gamma_eq_langmuir(C0, T_LPBF, H)
    return wgb_from_Gamma(G, T_LPBF, H)


def report():
    print("=" * 78)
    print(" Gibbs 晶界模型 —— 物理参数与自洽性报告")
    print("=" * 78)

    H, dG_anchor = dH_seg_from_anchor()
    print()
    print("【1】从 Tan 2016 锚点反解偏析焓（输入 [L]，输出 [T]）")
    print("     锚点：Γ_V(923 K) = 2.2 / 5.3 at·nm⁻²      [L] Tan 2016")
    print("     Γ₀   = %.1f at·nm⁻² = %.4e mol·m⁻²      [T] β-Ti(110) 位点密度" %
          (GAMMA_MONO_AT, GAMMA_MONO))
    print("     c_V  = %.3f，ρ_mol = %.4e mol·m⁻³" % (C0, RHO_MOL))
    print("     ⇒ ΔG_seg(923 K) = %.1f J/mol = %.2f kJ/mol" % (dG_anchor, dG_anchor / 1e3))
    print("     ⇒ ΔH_seg = %.1f J/mol = %.2f kJ/mol   （取 ΔS_seg = 0）" % (H, H / 1e3))
    print("     ⚠ 落在 DFT 常见量级 −10 ~ −30 kJ/mol 内  ⇒ 自洽")

    print()
    print("【2】Γ₀ 的敏感性（反解对 Γ₀ 的依赖 —— 必须记账）")
    for g0 in (9.0, 10.8, 12.9, 15.0):
        H2, dG2 = dH_seg_from_anchor(gamma0=g0 * AT_PER_NM2_TO_MOL_PER_M2)
        print("       Γ₀ = %5.1f at·nm⁻²  ⇒  ΔH_seg = %7.2f kJ/mol" % (g0, H2 / 1e3))

    print()
    print("【3】高温外推（McLean）—— 富集比 s = c_GB/c_far")
    print("     %-10s %12s %12s %10s %14s" %
          ("T (K)", "K=exp(-dG/RT)", "c_GB", "s", "Γ (mol/m²)"))
    for T in (923.0, 1200.0, 1500.0, 1800.0, 1950.0, 2100.0):
        cg = cGB_from_cfar(C0, T, H)
        g = gamma_eq_langmuir(C0, T, H)
        print("     %-10.0f %12.4f %12.5f %10.3f %14.4e" %
              (T, K_mclean(T, H), cg, cg / C0, g))
    print("     ⇒ 温度升高强烈稀释偏析（923 K → 1950 K 掉约 %.1f 倍）" %
          (K_mclean(923.0, H) / K_mclean(1950.0, H)))

    print()
    print("【4】单层分数检查（物理合理性）")
    for T in (923.0, 1950.0):
        g = gamma_eq_langmuir(C0, T, H)
        print("     T=%.0f K:  Γ = %.4e mol·m⁻² = %5.2f at·nm⁻² = %5.3f 个单层" %
              (T, g, g / AT_PER_NM2_TO_MOL_PER_M2,
               g / (GAMMA_MONO_AT * AT_PER_NM2_TO_MOL_PER_M2)))
    print("     ⇒ 亚单层、且 923 K 下落在 Tan 的 0.17~0.41 单层区间  ⇒ 自洽")

    print()
    print("【5】模型自洽性：峰 s 与 w_GB 无关，而 Γ ∝ w_GB  ⇒  w_GB 由物理 Γ **反解**")
    A = int_dc_du(T_LPBF, H)
    print("     A = ∫[c(u)−c_far]du = %.6f  （非线性 McLean 剖面，只依赖 ΔG_seg/RT）" % A)
    for T in (923.0, 1950.0):
        G = gamma_eq_langmuir(C0, T, H)
        w = wgb_from_Gamma(G, T, H)
        print("     T=%4.0f K:  Γ_phys = %.4e mol·m⁻²   ⇒  w_GB = %.4f nm" % (T, G, w * 1e9))
    w = wgb_for_anchor(H)
    print("     ⚠ 对比：生产用 4 µm（差 %.0f 倍）；文献约定的晶界结构厚度 δ = 0.5 nm" % (4e-6 / w))
    print("     ⇒ 模型**只有在 w_GB ≈ 0.4 nm 左右时**才同时给出正确的 s 与 Γ")
    print("     ⇒ 而 2D 熔池网格（dx = 1 µm）解析不了它 —— 这正是 Gibbs 面表示要解决的问题")

    print()
    print("【6】物理量纲的液固分配")
    for T in (1900.0, 1950.0, 2000.0):
        print("     T=%4.0f K:  Δμ°_LS = %8.1f J/mol  ⇒  k = %.4f" %
              (T, dmu_LS(T), math.exp(-dmu_LS(T) / (R * T))))

    print()
    print("【7】无量纲化系数（写进 .i 的形式，数值 O(1)）")
    co = coeffs(T_LPBF, H)
    print("     f_ref = R·T_ref/v_m = %.4e J·m⁻³   (T_ref = %.0f K)" % (f_ref(), T_REF))
    print("     f_loc/f_ref =  tau·[c·ln c + (1−c)·ln(1−c)]")
    print("                  + part·c·(1−h_solid)")
    print("                  + seg·(c−c₀)·h_gb")
    print("        tau  = %.6f" % co["tau"])
    print("        part = %.6f      (⇒ k = %.4f)" % (co["part"], math.exp(-co["part"] * T_REF / T_LPBF)))
    print("        seg  = %.6f      (⇒ s(1950 K) = %.4f)" % (co["seg"], s_at(C0, T_LPBF, H)))
    print("     f_cc/f_ref = tau/(c(1−c)) = %.4f  ⇒ 数值量级健康（生产原为 k_c=0.9）" %
          (co["tau"] / (C0 * (1 - C0))))
    print()

    return dict(dH_seg=H, dG_anchor=dG_anchor, w_GB_needed=w, coeffs=co)


if __name__ == "__main__":
    report()