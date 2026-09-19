#!/usr/bin/env python3
# =============================================================================
# 1D 固固晶界算例生成器（T11 晶界过剩 / T12 晶界快速扩散 / Phase 1.3 收尾）
# =============================================================================
#
# 【设计：冻结 η】
#   两个晶粒的序参量 η0、η1 用**解析剖面钉住**（FunctionAux），只让溶质 c 演化。
#   理由：本算例要测的是**溶质迁移率模型**，不是晶粒长大。
#   让 η 自由演化会把晶界迁移、拓扑事件、局部曲率全搅进来，
#   测到的偏差就分不清是迁移率错了还是别的错了（AGENTS.md §3.3 教训 12：
#   一次只改一个因素）。
#   仓库里 `tests/_mk_frozen_eta.py` 用的是同一套手法，只是那边是固液界面。
#
# 【晶界剖面】
#       eta0(x) = 0.5*(1 - tanh((x-x_gb)/w_gb))
#       eta1(x) = 0.5*(1 + tanh((x-x_gb)/w_gb))
#   ⇒ eta0 + eta1 = 1 处处成立；x = x_gb 处两者都 = 0.5（二元晶界中点）。
#
#   于是（与生产输入**完全相同的**指示函数）：
#       S      = eta0² + eta1²          晶粒内 = 1      晶界 = 0.5
#       Q      = eta0⁴ + eta1⁴          晶粒内 = 1      晶界 = 0.125
#       h_gb   = 8(S² − Q)              晶粒内 = 0      晶界 = 1     ← 关键
#       h_solid= min(1, 2S)             晶粒内 = 1      晶界 = 1     液相 = 0
#       D(η)   = D_L + (D_S−D_L)h_solid + (D_GB−D_S)h_gb
#              ⇒ 晶粒内 = D_S（D_L 项被 h_solid=1 消掉）
#              ⇒ 晶界   = D_GB
#       M      = D(η) / f_cc,  f_cc = k_c + 2A·S = ∂²F/∂c²（对 f_loc 精确）
#
# 【⚠ h_solid 为什么是 min(1, 2S)，而不是 S + h_gb(1−S)】
#   第一版用的是 h_solid = S + h_gb(1−S)。它在**晶界两翼**会失效，
#   而这一点是**用本算例量出来的**（不是推出来的）：
#       x=1.80 µm（S=0.607, h_gb=0.619）: h_solid 只有 0.850
#       ⇒ D = 6.26e-10 —— **比晶界中心的 4.00e-10 还大**（物理上反了：D 的
#          最大值跑到晶界两侧去了），而固相里的 D 比 D_S 大 2.6~584 倍。
#   根因：D_L 与 D_S 差 6300 倍时，液相项以 (1−h_solid) 的尾巴漏进固相。
#   ⇒ **固相指示必须在晶界处正好等于 1**，否则那个尾巴被 6300 倍放大。
#   min(1, 2S) 在 S=0.5（晶界中点）处恰好饱和到 1，两翼也全是 1；
#   固液界面处仍是 S 的线性混合（S=0.25 → 0.5），语义正确。
#   修复后实测：固相 D = 4.009e-13（期望 4.0e-13，+0.24%），
#               晶界 D = D_GB，且随远离晶界**单调下降**。
#   ⚠ 代价：min() 在 S=0.5 处有一个导数拐点（正好落在二元晶界中心线上）。
#     MOOSE 对 min() 取次梯度，实测牛顿正常收敛。
#
# 【为什么 h_gb = 8(S²−Q) 而不是 4S(1−S)】
#   4S(1−S) 在**固液界面中点**（S≈0.5）也等于 1 ⇒ 会把晶界快速扩散
#   错误地加到固液界面上。8(S²−Q) 只在「两个不同 η 同时非零」处非零。
#   本算例的 η0+η1≡1 恰好满足 S∈[0.5,1]，两种取法在**纯固固**下给同样的
#   h_gb（0→1），所以这里再加一条**固液判别**算式来体现差别（见 --sl-check）。
#
# 【T11 要测什么】
#   Γ_GB = ∫(c − c_grain) dx  —— 晶界溶质过剩量（单位面积）。
#   判据：Γ_GB 对 dx 与 w_gb **收敛**（不是「等于某个数」）。
#   ⇒ 本算例跑多档 dx × w_gb，看 Γ_GB 是否收敛。
#
# 【T12 要测什么】
#   晶界快速扩散：把 D_GB 调到远大于 D_S，看有效扩散是否真的变快，
#   并且量出的有效 D 与「D(x) 的调和/算术平均」预测一致。
#
# 用法：
#   python3 make_1d_gb.py --out gb.i                    # 默认
#   python3 make_1d_gb.py --out gb.i --dx 0.1e-6 --wgb 0.5e-6
#   python3 make_1d_gb.py --out gb.i --no-solute        # 只看 D 场（无溶质演化）
# =============================================================================

import argparse
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

K_C, A_PART, C0 = 0.9, 0.264, 0.036
KAPPA_C_DEFAULT = 1.0e-14


TEMPLATE = """# =============================================================================
# 1D 固固晶界算例（自动生成 —— 见 validated/make_1d_gb.py）
#   冻结 eta0/eta1，只演化溶质 c。迁移率用与生产**完全相同**的分层形式。
# =============================================================================
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = @NX@
  xmin = 0
  xmax = @LDOM@
[]

[Variables]
  @C_VAR@
  [w]
    initial_condition = 0
  []
[]

[Functions]
  [eta0_fn]
    type = ParsedFunction
    expression = '0.5*(1-tanh((x-@XGB@)/@WGB@))'
  []
  [eta1_fn]
    type = ParsedFunction
    expression = '0.5*(1+tanh((x-@XGB@)/@WGB@))'
  []
  [c_ic]
    type = ParsedFunction
    expression = '@C_EXPR@'
  []
[]

@ETA_AUX@

[Kernels]
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    # 【必须】M 依赖 eta0/eta1，不声明则 ∂M/∂η 整块不进雅可比（同审计 P0-1）
    coupled_variables = 'eta0 eta1'
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
    coupled_variables = 'eta0 eta1'
  []
[]

[Materials]
  [ch_kappa]
    type = GenericConstantMaterial
    prop_names  = 'kappa_c'
    prop_values = '@KAPPA_C@'
  []

  # ===== 与生产输入完全相同的指示函数与分层迁移率 =====
  [S_eta2]
    type = DerivativeParsedMaterial
    property_name = S_eta2
    coupled_variables = 'eta0 eta1'
    expression = 'eta0^2+eta1^2'
    derivative_order = 2
  []
  [Q_eta4]
    type = DerivativeParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'eta0 eta1'
    expression = 'eta0^4+eta1^4'
    derivative_order = 2
  []
  [h_gb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'eta0 eta1'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []
  [h_solid]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'eta0 eta1'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
    derivative_order = 2
  []
  [D_field]
    type = DerivativeParsedMaterial
    property_name = D_eff
    coupled_variables = 'eta0 eta1'
    material_property_names = 'h_gb h_solid'
    constant_names = 'D_L D_S D_GB'
    constant_expressions = '@DL@ @DS@ @DGB@'
    expression = 'D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb'
    derivative_order = 2
  []
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'eta0 eta1'
    material_property_names = 'D_eff @M_PROPS@'
    constant_names = 'k_c A_part'
    constant_expressions = '0.9 0.264'
    # ⚠ 这里必须是 f_loc 对 c 的**二阶导** f_cc。
    #   换 `--f-part` 会同时改 f_loc 与这里 —— **两处必须一致**，
    #   否则 D = M·f_cc 不再成立（T6 的判据就是查这个）。
    expression = 'D_eff / (@M_FCC@)'
    derivative_order = 2
  []

  # 自由能：与生产 f_loc 同形式（S = Ση²）
  #
  # 【Phase 3 第一增量】`--f-seg` 打开后追加一项**独立的晶界偏析项**：
  #
  #     f_seg = (Omega0 / wgb) * (c - c0) * h_gb          （Omega0 < 0 ⇒ 晶界富集）
  #
  # **为什么必须带 1/wgb**：弥散界面模型里，任何"只在晶界处非零"的自由能项，
  #   其产生的溶质过剩 Γ_GB = ∫(c − c_grain)dx 会**正比于晶界宽度** ——
  #   这正是实测到的 `Γ_GB ∝ w_gb`（T11，+101.9% / +103.9%）。
  #   而晶界能那一半（κ、μ0）**是有配套 wGB 重标定的**，所以 σ 逐位不变。
  #   ⇒ 偏析这一项缺的就是它的重标定。加上 1/wgb 之后：
  #        Δc ≈ −Ω/(k_c + A_part) ∝ 1/wgb ，而剖面宽度 ∝ wgb
  #        ⇒ Γ_GB ≈ Δc × 宽度 = **与 wgb 无关** ✓
  #
  # ⚠ `Omega0` 是 **calibration 参数，不是 Ti64 材料常数**（审计禁止事项 5）。
  #   它的量级要标到与文献的 Γ_GB 可比（当前唯一可用的锚点是
  #   Tan 2016 的 α/β 界面 V 过剩 +2.2~5.3 at·nm⁻²，见 GB_SEGREGATION_LITERATURE.md）。
  #
  # ⚠ 线性项 `Ω·c·h_gb` 对 c 的**二阶导为零** ⇒ f_cc = k_c + 2·A_part·S 不变
  #   ⇒ 上面 [solute_mobility] 的 M = D_eff/f_cc **不需要改** ✓（这一点很省事，
  #   但换别的偏析形式（如二次项）就必须同步改 M，否则 D = M·∂²f/∂c² 不再成立）。
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c eta0 eta1'
    material_property_names = '@F_LOC_PROPS@'
    constant_names = '@F_LOC_CONSTS@'
    constant_expressions = '@F_LOC_VALS@'
    expression = '@F_LOC_EXPR@'
    derivative_order = 2
  []
[]

[Postprocessors]
  # --- 守恒（T2）---
  [total_c]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'timestep_end'
  []
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'timestep_end'
  []
  # --- 晶界过剩 Γ_GB = ∫(c − c_far) dx（T11）---
  # ⚠ 参考值必须取**远场**（边界处的当前值），**不能**取初值 c_grain。
  #   封闭系统里 ∫c dx 严格守恒，而 ∫c_grain dx 是常数
  #   ⇒ ∫(c − c_grain)dx **恒等于 0**（晶界的富集与旁边的贫化正好抵消）。
  #   实测踩过这个坑：gamma_gb 读数 -3.3e-21，看起来像"没有晶界过剩"，
  #   其实定义就是错的。见 validated/VALIDATION_STATUS.md。
  [c_total]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'timestep_end'
  []
  [c_edge]
    type = ElementalVariableValue
    variable = c
    elementid = 0
    execute_on = 'timestep_end'
  []
  [gamma_gb]
    type = ParsedPostprocessor
    expression = 'c_total - c_edge * @LDOM_NUM@'
    pp_names = 'c_total c_edge'
    execute_on = 'timestep_end'
  []
  # --- 直接在真实运行里量 D 与 h_gb（比 Python 核对强：走的是 MOOSE 自己的组装）---
  [D_at_gb]
    type = ElementalVariableValue
    variable = D_aux
    elementid = @IEL_GB@
    execute_on = 'initial timestep_end'
  []
  [D_in_grain]
    type = ElementalVariableValue
    variable = D_aux
    elementid = @IEL_GRAIN@
    execute_on = 'initial timestep_end'
  []
  [hgb_at_gb]
    type = ElementalVariableValue
    variable = hgb_aux
    elementid = @IEL_GB@
    execute_on = 'initial timestep_end'
  []
  [hgb_in_grain]
    type = ElementalVariableValue
    variable = hgb_aux
    elementid = @IEL_GRAIN@
    execute_on = 'initial timestep_end'
  []
  # --- 与取样位置无关的极值量（判据用这两个，不用 D_at_gb）---
  # ⚠ 单元常量（MONOMIAL）取的是**第一个求积点**的值，不是质心 ——
  #   所以 D_at_gb 天然带一个小偏差，不该拿来当判据。
  #   D_min 则精确：远离晶界处 h_gb≡0，D = D_S 逐位成立。
  [D_min]
    type = ElementExtremeValue
    variable = D_aux
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [D_max]
    type = ElementExtremeValue
    variable = D_aux
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [hgb_max]
    type = ElementExtremeValue
    variable = hgb_aux
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [hgb_min]
    type = ElementExtremeValue
    variable = hgb_aux
    value_type = min
    execute_on = 'initial timestep_end'
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  l_max_its = 50
  l_tol = 1e-8
  nl_max_its = 30
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  dt = @DT@
  end_time = @TEND@
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = @DT@
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 8
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
"""


# η 冻结模式追加的块
ETA_AUX = """[AuxVariables]
  [eta0]
  []
  [eta1]
  []
  # ⚠ MaterialRealAux 只能写**单元常量**（MONOMIAL/CONSTANT）辅助变量，
  #   写成节点变量会报 "Nodal AuxKernel attempted to reference material property"。
  [D_aux]
    order = CONSTANT
    family = MONOMIAL
  []
  [hgb_aux]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [eta0_fix]
    type = FunctionAux
    variable = eta0
    function = eta0_fn
    execute_on = 'initial timestep_end'
  []
  [eta1_fix]
    type = FunctionAux
    variable = eta1
    function = eta1_fn
    execute_on = 'initial timestep_end'
  []
  [D_out]
    type = MaterialRealAux
    variable = D_aux
    property = D_eff
    execute_on = 'initial timestep_end'
  []
  [hgb_out]
    type = MaterialRealAux
    variable = hgb_aux
    property = h_gb
    execute_on = 'initial timestep_end'
  []
[]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dx", type=float, default=0.05e-6, help="网格间距 m")
    ap.add_argument("--ldom", type=float, default=4.0e-6, help="域长 m")
    ap.add_argument("--wgb", type=float, default=0.4e-6, help="晶界 tanh 宽度 m")
    ap.add_argument("--dl", type=float, default=2.52e-9)
    ap.add_argument("--ds", type=float, default=4.0e-13)
    ap.add_argument("--dgb", type=float, default=4.0e-10)
    ap.add_argument("--kc", type=float, default=KAPPA_C_DEFAULT)
    ap.add_argument("--t-end", type=float, default=1.0e-6)
    ap.add_argument("--f-part", choices=("S", "h_solid"), default="S",
                    help="Phase 3 第二增量：分配项由什么驱动。"
                         "`S`（默认）= Ση²，晶界处 =0.5 ⇒ **在固固晶界上凭空造出"
                         "分配驱动力**，其宽度 ∝ wGB ⇒ Γ_GB 残余的 wGB 依赖就来自这里。"
                         "`h_solid` = 固相指示（晶粒内与晶界处**都是 1**，只在固液界面不同）"
                         "⇒ 固固晶界上处处相同、不产生过剩。"
                         "⚠ 会同步改 M 的 f_cc（必须一起改，否则 D = M·f_cc 破）。")
    ap.add_argument("--f-seg", type=float, default=None, metavar="OMEGA0",
                    help="Phase 3 第一增量：打开独立的晶界偏析项 "
                         "f_seg = (OMEGA0/wgb)*(c-c0)*h_gb。（负值 ⇒ 晶界富集）"
                         "⚠ OMEGA0 是 **calibration 参数**，不是 Ti64 材料常数。")
    args = ap.parse_args()

    n = int(round(args.ldom / args.dx))

    # ⚠ 把晶界对准**单元质心**，而不是节点。
    #   原因：h_gb、D_aux 都是 CONSTANT MONOMIAL（单元常量），它们的值在单元质心处取值。
    #   若把晶界放在节点上（x = n/2·dx），两侧单元的质心都偏离晶界，
    #   量到的 h_gb 只有 0.9897、D 也只有 0.99·D_GB —— 会被误读成"模型差 1%"。
    #   放在质心上则判据变成**精确等式**：h_gb = 1、D = D_GB。
    iel_gb = n // 2
    x_gb = (iel_gb + 0.5) * args.dx

    # 晶粒内平衡浓度：c = c0*k_c/(k_c+2A*S)，S=1
    c_grain = C0 * K_C / (K_C + 2.0 * A_PART)
    # 初值：晶粒内取平衡值，晶界处按 S=0.5 的平衡值加一点盈余
    c_ic = f"{c_grain:.10g}"

    # iel_gb 已在上面按「质心对准」定好，这里不要再重算
    iel_grain = max(1, int(round(0.1 * args.ldom / args.dx)))

    # ⚠ 顺序：ETA_AUX 是在其它占位符替换**之后**才插入的，
    #   所以它内部的占位符必须先自己替换掉，否则会漏网。
    eta_aux = ETA_AUX.replace("@C_GRAIN@", f"{c_grain:.10g}")

    # --- Phase 3 增量：f_loc 的分配项驱动 + 可选偏析项 ---
    #   默认（--f-part S，无 --f-seg）时，下面各项拼出来与改前**逐字相同**。
    part = "h_solid" if args.f_part == "h_solid" else "S_eta2"
    f_props = [part]
    f_consts = ["k_c", "c0", "A_part"]
    f_vals = ["0.9", "0.036", "0.264"]
    f_expr = "k_c/2*(c-c0)^2 + A_part*c^2*%s" % part
    # ⚠ M 的 f_cc 必须与 f_loc 的分配项**一致**
    m_fcc = "k_c + 2*A_part*%s" % part
    if args.f_seg is not None:
        f_props.append("h_gb")
        f_consts += ["Omega0", "wgb"]
        f_vals += ["%.10g" % args.f_seg, "%.10g" % args.wgb]
        f_expr += " + (Omega0/wgb)*(c-c0)*h_gb"
    f_props, f_consts, f_vals = " ".join(f_props), " ".join(f_consts), " ".join(f_vals)

    txt = (TEMPLATE
           .replace("@NX@", str(n))
           .replace("@LDOM@", f"{args.ldom:.6e}")
           .replace("@LDOM_NUM@", f"{args.ldom:.10g}")
           .replace("@XGB@", f"{x_gb:.6e}")
           .replace("@WGB@", f"{args.wgb:.6e}")
           .replace("@KAPPA_C@", f"{args.kc:.6e}")
           .replace("@F_LOC_PROPS@", f_props)
           .replace("@F_LOC_CONSTS@", f_consts)
           .replace("@F_LOC_VALS@", f_vals)
           .replace("@F_LOC_EXPR@", f_expr)
           .replace("@M_PROPS@", part)
           .replace("@M_FCC@", m_fcc)
           .replace("@DL@", f"{args.dl:g}")
           .replace("@DS@", f"{args.ds:g}")
           .replace("@DGB@", f"{args.dgb:g}")
           .replace("@IEL_GB@", str(iel_gb))
           .replace("@IEL_GRAIN@", str(iel_grain))
           .replace("@DT@", f"{args.t_end / 100:.6e}")
           .replace("@TEND@", f"{args.t_end:.6e}")
           .replace("@C_EXPR@", c_ic)
           .replace("@C_GRAIN@", f"{c_grain:.10g}")
           .replace("@C_VAR@", "[c]\n    initial_condition = " + c_ic + "\n  []")
           .replace("@ETA_AUX@", eta_aux))

    # 自检：不该有未替换的占位符
    left = re.findall(r"@[A-Z_]+@", txt)
    if left:
        sys.exit(f"错误：还有未替换的占位符 {sorted(set(left))}")

    open(args.out, "w", encoding="utf-8", newline="").write(txt)

    print(f"写出 {args.out}")
    print(f"  网格 nx={n}, dx={args.dx:.3e} m, 域长 {args.ldom:.3e} m")
    print(f"  晶界 x={x_gb:.3e} m, w_gb={args.wgb:.3e} m "
          f"({args.wgb/args.dx:.1f} 单元), 取样单元 GB={iel_gb} 晶粒={iel_grain}")
    print(f"  D_L={args.dl:g}  D_S={args.ds:g}  D_GB={args.dgb:g}")
    print(f"  晶粒内平衡浓度 c_grain = {c_grain:.8f}")
    print()
    print("  预期（自检用）：")
    print(f"    晶界单元   D_eff -> D_GB = {args.dgb:g}      h_gb -> 1")
    print(f"    晶粒单元   D_eff -> D_S  = {args.ds:g}      h_gb -> 0")


if __name__ == "__main__":
    main()
