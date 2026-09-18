#!/usr/bin/env python3
# =============================================================================
# ④ 修复的判别算例：熔化区里 η 会不会越过 1
# =============================================================================
#
# 【机理（这是越界的真正来源，已从源码推出）】
#   ACGrGrPoly.C:61  残差 = mu*(η³ − η + 2γ·η·Σ_{j≠i}η_j²)
#   ⇒ 体自由能 f = mu*[ Σ(η⁴/4 − η²/2) + γ Σ_{i<j} η_i²η_j² ]
#
#   液相里 mu < 0，于是两项同时变号：
#     (a) 四次项 mu·Ση⁴/4 < 0  ⇒ f 在 η→∞ 时 → −∞   （自由能**下无界**）
#     (b) 交叉项 mu·γΣη_i²η_j² < 0 ⇒ **吸引**：两个序参量互相把对方往上拉
#
#   (b) 是越界的直接推手：取 η_1=1、η_2=0.3、mu<0，则
#       ∂f/∂η_1 = mu*(1 − 1 + 2γ·0.09) = 0.27·mu < 0  ⇒ 把 η_1 往上推
#   ⇒ η_1 冲过 1，且因为 (a) 没有任何回复力，停不下来。
#
# 【新形式（Landau）：温度只进二次项】
#   f = mu0*Σ(η⁴/4) − mu*Σ(η²)/2 + mu0*γ Σ_{i<j}η_i²η_j² ,  mu0 = 9e5 > 0
#   ⇒ 四次项与交叉项的系数**恒正**，(a)(b) 两个病根同时消失。
#   驻点满足 η_i² = mu/mu0 − 2γΣ_{j≠i}η_j²  ≤  mu/mu0 = s  ⇒  **η ≤ 1（当 s ≤ 1）**
#
# 【本算例】
#   1D，两个序参量在 x≈10 µm 处交叠成晶界，全场 mu = −2·mu0（强液相）。
#   变体 old = ACGrGrPoly（原模型），变体 new = AllenCahn + Landau F。
#   两者**同时输出两个自由能的体积分**，可直接对比。
#
# 用法：  python3 make_melt_ab.py     （生成 /root/work/g1/melt_ab/{old,new}/melt.i）
# =============================================================================
import io
import os

OUT = "/root/work/g1/melt_ab"

L_MOB = 0.095673      # = 4/3*M_GB/wGB，T=1830 K 的 Arrhenius 值
KAPPA = 1.8e-6
GAMMA = 1.5
MU0 = 9.0e5
MU = -2.0 * MU0       # 强液相（生产里 T→高温时 mu → −2*mu0）

BULK_OLD = """\
  [ACBulk0]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr1'
    mob_name = L
  []
  [ACBulk1]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0'
    mob_name = L
  []
"""

BULK_NEW = """\
  [ACBulk0]
    type = AllenCahn
    variable = gr0
    f_name = F
    mob_name = L
    coupled_variables = 'gr1'
  []
  [ACBulk1]
    type = AllenCahn
    variable = gr1
    f_name = F
    mob_name = L
    coupled_variables = 'gr0'
  []
"""

TEMPLATE = """\
# 自动生成，请勿手改。生成器：tests/make_melt_ab.py   变体 = {variant}
# mu = {mu:g}  (mu0 = {mu0:g} ⇒ s = mu/mu0 = {s:.4g})
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 200
  xmin = 0.0
  xmax = 2.0e-5
[]

[GlobalParams]
  op_num = 2
  var_name_base = gr
[]

[Variables]
  [PolycrystalVariables]
  []
[]

[ICs]
  [gr0_ic]
    type = FunctionIC
    variable = gr0
    function = ic0
  []
  [gr1_ic]
    type = FunctionIC
    variable = gr1
    function = ic1
  []
[]

[Functions]
  [ic0]
    type = ParsedFunction
    expression = '0.5*(1+tanh((x-8.0e-6)/1.0e-6))'
  []
  [ic1]
    type = ParsedFunction
    expression = '0.5*(1-tanh((x-12.0e-6)/1.0e-6))'
  []
[]

[Kernels]
  [dgr0dt]
    type = TimeDerivative
    variable = gr0
  []
  [dgr1dt]
    type = TimeDerivative
    variable = gr1
  []
{bulk}
  [ACInt0]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
    variable_L = false
  []
  [ACInt1]
    type = ACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
    variable_L = false
  []
[]

[Materials]
  [params]
    type = GenericConstantMaterial
    prop_names  = 'L        kappa_op  gamma_asymm  mu0      mu'
    prop_values = '{L:g} {kappa:g}    {gamma:g}       {mu0:g}    {mu:g}'
  []

  # 原模型自由能（仅诊断；new 变体里没有任何核消费它）
  [f_old]
    type = DerivativeParsedMaterial
    property_name = f_old
    coupled_variables = 'gr0 gr1'
    material_property_names = 'mu gamma_asymm'
    expression = 'mu*((gr0^4/4-gr0^2/2)+(gr1^4/4-gr1^2/2)+gamma_asymm*gr0^2*gr1^2)'
    derivative_order = 1
  []

  # Landau 形式（new 变体的实际自由能；old 变体里仅诊断）
  [F]
    type = DerivativeParsedMaterial
    property_name = F
    coupled_variables = 'gr0 gr1'
    material_property_names = 'mu0 mu gamma_asymm'
    expression = 'mu0*(gr0^4/4+gr1^4/4) - mu*(gr0^2+gr1^2)/2 + mu0*gamma_asymm*gr0^2*gr1^2'
    derivative_order = 2
  []
[]

[AuxVariables]
  [sum2]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [sum2]
    type = ParsedAux
    variable = sum2
    coupled_variables = 'gr0 gr1'
    expression = 'gr0^2+gr1^2'
    execute_on = 'initial timestep_end'
  []
[]

[Postprocessors]
  [gr0_max]
    type = NodalExtremeValue
    variable = gr0
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [gr1_max]
    type = NodalExtremeValue
    variable = gr1
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [sum2_max]
    type = ElementExtremeValue
    variable = sum2
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [F_old]
    type = ElementIntegralMaterialProperty
    mat_prop = f_old
    execute_on = 'initial timestep_end'
  []
  [F_new]
    type = ElementIntegralMaterialProperty
    mat_prop = F
    execute_on = 'initial timestep_end'
  []
  [n_nonlin]
    type = NumNonlinearIterations
    execute_on = 'timestep_end'
  []
  [dt]
    type = TimestepSize
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  l_max_its = 50
  l_tol = 1e-10
  nl_max_its = 50
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  end_time = 6.0e-5
  dtmax = 2.0e-6
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 2.0e-7
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 8
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  [exo]
    type = Exodus
    time_step_interval = 10
  []
[]
"""


def main():
    for variant, bulk in (("old", BULK_OLD), ("new", BULK_NEW)):
        # bulk 块缩进对齐（模板里占位符在 [Kernels] 内，需自带 2 空格缩进）
        txt = TEMPLATE.format(variant=variant, bulk=bulk.rstrip("\n"),
                              mu=MU, mu0=MU0, s=MU / MU0,
                              L=L_MOB, kappa=KAPPA, gamma=GAMMA)
        d = os.path.join(OUT, variant)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "melt.i")
        io.open(p, "w", encoding="utf-8", newline="").write(txt)
        print("已写 %s" % p)
    print()
    print("mu  = %.6g   mu0 = %.6g   s = mu/mu0 = %.4g  (强液相)" % (MU, MU0, MU / MU0))


if __name__ == "__main__":
    main()
