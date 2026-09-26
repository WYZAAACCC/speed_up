#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 2D 生产副本改造成 **Gibbs 面模型**版本。

输入： pipeline/gibbs/stage1_meltpool_gibbs.i（= stage1_meltpool_c.i 的逐位副本）
输出： 原地改造（先在 .orig 留一份备份）

改造内容（**只动溶质轨道**，拓扑轨道一个字不动）
------------------------------------------------
1. 体相自由能 → **物理量纲**：f_loc/f_ref = τ[c·ln c+(1−c)ln(1−c)] − part·c·(1−h_solid)
   （删除无量纲的 k_c/2(c−c0)² 与 A_part·c²·min(1,2S) 与 Ω₀ 偏析项）
2. 迁移率 M = D_eff/(f_ref·τ/(c(1−c))) ⇒ **D = M·f_cc 逐点精确**
   ⇒ 审计 P0-4（固相扩散反比液相快 1.59 倍）由构造消除
3. **新增低维 Γ 状态量** + 它的方程 + 体相源项（1D 已验证的 MatReaction 方案）
   ⇒ Γ 不再挂在 wGB 上 ⇒ **s 与 Γ 可以同时对**
4. 指示函数全部**内联**（教训 28：DerivativeParsedMaterial 只对字面变量发射导数）

⚠ 用行首锚定的块匹配（教训 6），并且打印每个块的替换结果供人工核对。
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # .../pipeline/gibbs/validated
GIBBS_DIR = os.path.dirname(HERE)                           # .../pipeline/gibbs
SRC = os.path.join(GIBBS_DIR, "stage1_meltpool_gibbs.i")

# ---- 物理参数（由 gibbs_physics 供；这里直接写死以保证 .i 自包含、可复现）----
T_REF = 1950.0
F_REF = 1.6423e9          # R*T_ref/v_m
DH_SEG = -11931.1         # 由 Tan 2016 锚点 + δ_GB=0.5nm 解出（gibbs_physics）
DS_SEG = 0.0
GAMMA_MONO = 2.1421e-5    # mol/m^2  单层饱和
GAMMA_MONO_AT = 12.9
C0 = 0.036
K_ATT = 1.0e6             # 1/s 附着速率 [A] 标定值
K_PART = 0.63


def sub_block(text, name, new_block):
    """用行首锚定的正则替换 [Materials]/[name] 块（AGENTS.md 教训 6）。"""
    pat = re.compile(r"(^[ \t]*\[" + re.escape(name) + r"\](?:.*?))\n[ \t]*\[\]",
                     re.S | re.M)
    m = pat.search(text)
    if not m:
        return text, False
    return text[:m.start()] + new_block.rstrip("\n") + text[m.end():], True


ETA_S = "(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)"
ETA_Q = "(gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4)"
HGB = "8*(%s^2 - %s)" % (ETA_S, ETA_Q)
HSOL = "min(1, 2*%s)" % ETA_S
ALLETA = "gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7"

FREE_ENERGY = """  # ===========================================================================
  # 【Gibbs 版 1】体相自由能 —— **物理量纲**（理想溶液 + 液固分配）
  # ===========================================================================
  #   f_loc/f_ref = tau*[c*log(c) + (1-c)*log(1-c)] - part*c*(1-h_solid)
  #   其中 f_ref = R*T_ref/v_m = %.4e J/m^3,  tau = T/T_ref = T/%.1f
  #        part = -R*T*log(k)/(R*T_ref)  ⇒ 理想溶液下平衡给出 k = exp(-part*tau^-1 的对应值)
  #
  # ⚠ 与生产的区别：
  #   生产: k_c/2*(c-c0)^2 + A_part*c^2*min(1,2S) + (Omega0/wgb)*(c-c0)*h_gb
  #         —— 无量纲（k_c=0.9 vs 物理 f_cc≈4.7e10 J/m^3），且**无温度依赖**。
  #   本版: 理想溶液 ⇒ **精确 McLean 等温线**、自带正确的温度依赖、量纲为 J/m^3。
  #
  # ⚠ 偏析项已**搬走**：不再用 Omega0/h_gb，改由独立的低维 Gamma 状态量承担
  #    （见 [gam_*] 与 [shape]/[hgb_katt_As] 等材料）。这样 Γ 不再 ∝ wGB。
  # ===========================================================================
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c T %s'
    constant_names = 'FREF TREF C0 KPART'
    constant_expressions = '%.6e %.6e %.6g %.6g'
    expression = 'FREF*( (T/TREF)*(c*log(c)+(1-c)*log(1-c))
                          - (-log(KPART))*c*(1-%s) )'
    derivative_order = 2
  []""" % (F_REF, T_REF, ALLETA, F_REF, T_REF, C0, K_PART, HSOL)

MOBILITY = """  # ===========================================================================
  # 【Gibbs 版 2】迁移率 M = D_eff / f_cc   —— D = M*f_cc **逐点精确**
  # ===========================================================================
  #   f_cc = f_ref*(T/T_ref)/(c(1-c))      （理想溶液，物理量纲）
  #   D_eff = D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb
  #   ⇒ 固相 D=D_S、晶界 D=D_GB、液相 D=D_L  —— 审计 P0-4（固相反比液相快）消失
  # ⚠ 生产用 f_cc = k_c + 2*A_part*min(1,2S)（无量纲），
  #   所以 D_S/D_L 是被那个无量纲比值扭曲的；这里由构造修正。
  # ===========================================================================
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'c T %s'
    constant_names = 'FREF TREF DL DS DGB'
    constant_expressions = '%.6e %.6e 1.2e-06 4.0e-13 4.0e-10'
    expression = '(DL + (DS-DL)*%s + (DGB-DS)*(%s)) / (FREF*(T/TREF)/(c*(1-c)))'
    derivative_order = 2
  []""" % (ALLETA, F_REF, T_REF, HSOL, HGB)

# --- 新增：Gibbs 面相关材料（全部内联，保证导数发射）---
GIBBS_MATERIALS = """
  # ===========================================================================
  # 【Gibbs 版 3】低维 Γ 的速率材料（1D 已验证方案，见 validated/run_1d_gb_gam.sh）
  # ===========================================================================
  #   Γ 方程:  dΓ/dt = h_gb*k_att*(Gamma_eq - Γ),   Gamma_eq = GAM0*exp(-dG_seg/(R*T))*c
  #   体相源:  ∂c/∂t = ∇·(D∇c) - shape*∂Γ/∂t
  #            shape*∂Γ/∂t = shape*h_gb*k_att*GAM0*K(T)*c - shape*h_gb*k_att*Γ
  #   shape = h_gb/(4/3*wGB),  ∫shape dx = 1  ⇒ **总量与 wGB 无关**
  #
  # ⚠ 所有 rate 都**不含 c 与 Gamma**（只含 T 与 η）⇒ MatReaction 的 Jacobian
  #   只需要 rate 本身，不需要它的导数 ⇒ 不会踩"静默取 0"的坑。
  # ⚠ 但 MatReaction 会无条件请求 drate/dc 与 drate/dGamma ⇒ 这两个 0 导数是
  #   在本材料里**显式声明** c 与 Gam 才存在的（否则报 "not defined"）。
  # ===========================================================================
  [shape]
    type = DerivativeParsedMaterial
    property_name = shape
    coupled_variables = 'c Gam T %s'
    constant_names = 'WGB'
    constant_expressions = '4.0e-06'
    expression = '(%s)/((4.0/3.0)*WGB)'
    derivative_order = 2
  []
  [hgb_katt_As]
    type = DerivativeParsedMaterial
    property_name = hgb_katt_As
    coupled_variables = 'c Gam T %s'
    constant_names = 'KATT GAM0 DHSEG DSSEG RGAS'
    constant_expressions = '%.6e %.6e %.6e %.6e 8.314462618'
    expression = 'KATT*GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))*(%s)'
    derivative_order = 2
  []
  [hgb_katt]
    type = DerivativeParsedMaterial
    property_name = hgb_katt
    coupled_variables = 'c Gam T %s'
    constant_names = 'KATT'
    constant_expressions = '%.6e'
    expression = 'KATT*(%s)'
    derivative_order = 2
  []
  [neg_hgb_katt]
    type = DerivativeParsedMaterial
    property_name = neg_hgb_katt
    coupled_variables = 'c Gam T %s'
    constant_names = 'KATT'
    constant_expressions = '%.6e'
    expression = '-KATT*(%s)'
    derivative_order = 2
  []
  [shape_hgb_katt]
    type = DerivativeParsedMaterial
    property_name = shape_hgb_katt
    coupled_variables = 'c Gam T %s'
    constant_names = 'KATT WGB'
    constant_expressions = '%.6e 4.0e-06'
    expression = 'KATT*(%s)^2/((4.0/3.0)*WGB)'
    derivative_order = 2
  []
  [neg_shape_hgb_katt_As]
    type = DerivativeParsedMaterial
    property_name = neg_shape_hgb_katt_As
    coupled_variables = 'c Gam T %s'
    constant_names = 'KATT GAM0 DHSEG DSSEG RGAS WGB'
    constant_expressions = '%.6e %.6e %.6e %.6e 8.314462618 4.0e-06'
    expression = '-KATT*GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))*(%s)^2/((4.0/3.0)*WGB)'
    derivative_order = 2
  []
""" % (ALLETA, HGB, ALLETA, K_ATT, GAMMA_MONO, DH_SEG, DS_SEG, HGB,
       ALLETA, K_ATT, HGB, ALLETA, K_ATT, HGB, ALLETA, K_ATT,
       HGB, ALLETA, K_ATT, GAMMA_MONO, DH_SEG, DS_SEG, HGB)

GIBBS_KERNELS = """
  # ===========================================================================
  # 【Gibbs 版 4】体相源项：∂c/∂t += -shape*∂Γ/∂t（代回 Γ 方程后是两个 MatReaction）
  # ===========================================================================
  #   + shape*h_gb*k_att*As*c   -> rate = neg_shape_hgb_katt_As（v 留空 = 本变量）
  #   - shape*h_gb*k_att*Γ      -> rate = shape_hgb_katt, v = Gam
  # ⚠ MatReaction 的 args 必须列出 rate 依赖的全部**非线性**变量（这里是 8 个 η），
  #   否则雅可比缺块（审计 P0-1 同类；AGENTS.md §3.1 坑 3 的告警要当错误看）。
  # ===========================================================================
  [c_src_c]
    type = MatReaction
    variable = c
    reaction_rate = neg_shape_hgb_katt_As
    args = '%s'
  []
  [c_src_gam]
    type = MatReaction
    variable = c
    v = Gam
    reaction_rate = shape_hgb_katt
    args = '%s'
  []
  # ---------------------------------------------------------------------------
  # 【Gibbs 版 5】晶界 Γ 的演化：dΓ/dt = h_gb*k_att*(As*c - Γ)
  # ---------------------------------------------------------------------------
  [gam_dt]
    type = TimeDerivative
    variable = Gam
  []
  [gam_eq]
    type = MatReaction
    variable = Gam
    v = c
    reaction_rate = hgb_katt_As
    args = '%s'
  []
  [gam_relax]
    type = MatReaction
    variable = Gam
    reaction_rate = neg_hgb_katt
    args = '%s'
  []
""".replace("%s", ALLETA)

GIBBS_VARS = """  [Gam]
    # 低维 Gibbs 过剩 Γ（单位 mol/m^2）。只在 h_gb 非零处被驱动；
    # 体相通过 -shape*dΓ/dt 与它交换溶质。初值给 0，由方程弛豫到 Γ_eq。
    initial_condition = 0
  []
"""


def main():
    with open(SRC, encoding="utf-8", newline="") as f:
        txt = f.read()
    orig = txt

    if not os.path.exists(SRC + ".orig"):
        shutil.copyfile(SRC, SRC + ".orig")
        print("备份 -> %s.orig" % os.path.basename(SRC))

    # --- 2a. 替换体相自由能 ---
    txt, ok = sub_block(txt, "free_energy", FREE_ENERGY)
    print("  [free_energy]      替换 %s" % ("OK" if ok else "**未命中**"))

    # --- 2b. 替换迁移率 ---
    txt, ok = sub_block(txt, "solute_mobility", MOBILITY)
    print("  [solute_mobility]  替换 %s" % ("OK" if ok else "**未命中**"))

    # --- 2c. at_susc 内联 h_gb（教训 28）---
    txt, ok = sub_block(txt, "at_susc", """  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = 'c w %s'
    constant_names = 'ALPHA W k_eq'
    constant_expressions = '2 2e-06 0.6303'
    expression = 'ALPHA*W*(1-k_eq)*c*(1-(%s)) + 0*w'
    derivative_order = 2
  []""" % (ALLETA, HGB))
    print("  [at_susc]          内联 h_gb %s" % ("OK" if ok else "**未命中**"))

    # --- 2d. 追加 Gibbs 材料（插在 [Materials] 闭合之前）---
    m = re.search(r"^\[Materials\]", txt, re.M)
    if not m:
        sys.exit("找不到 [Materials]")
    # 找 [Materials] 之后第一个行首 []
    m2 = re.compile(r"^\[\]", re.M).search(txt, m.end())
    if not m2:
        sys.exit("找不到 [Materials] 的结束")
    txt = txt[:m2.start()] + GIBBS_MATERIALS.lstrip("\n") + "\n" + txt[m2.start():]
    print("  [Materials]        追加 Gibbs 速率材料 OK")

    # --- 2e. 追加 kernels（插在 [Kernels] 闭合之前）---
    m = re.search(r"^\[Kernels\]", txt, re.M)
    m2 = re.compile(r"^\[\]", re.M).search(txt, m.end())
    txt = txt[:m2.start()] + GIBBS_KERNELS.strip("\n") + "\n" + txt[m2.start():]
    print("  [Kernels]          追加 Gibbs 核 OK")

    # --- 2f. 追加变量 Gam ---
    m = re.search(r"^\[Variables\]", txt, re.M)
    m2 = re.compile(r"^\[\]", re.M).search(txt, m.end())
    txt = txt[:m2.start()] + GIBBS_VARS + txt[m2.start():]
    print("  [Variables]        追加 Gam OK")

    with open(SRC, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    print()
    print("行数 %d -> %d" % (orig.count("\n"), txt.count("\n")))
    print("写出 %s" % SRC)


if __name__ == "__main__":
    main()