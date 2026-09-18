# =============================================================================
# ④ 修复的回归算例：Landau 形式 vs 原 GrainGrowth(ACGrGrPoly) 形式
# =============================================================================
#
# 【要证的事】
#   新的自由能写在 s = mu/mu0 = 1 时，必须**逐项等价于**原模型
#       f_原 = mu*[ Σ(η⁴/4 − η²/2) + γ Σ_{i<j} η_i²η_j² ]
#       f_新 = mu0*Σ(η⁴/4) − mu*Σ(η²)/2 + mu0*γ Σ_{i<j} η_i²η_j²
#   当 mu = mu0 时两者恒等。
#
#   本算例的 mu = 9.0e5 = mu0 ⇒ **s = 1**，所以两版必须给出同一个解。
#   对照组 = grain_growth_circle.i（用 [Modules][PhaseField][GrainGrowth]，即 ACGrGrPoly）。
#
# 【与对照组的唯一差别】
#   GrainGrowth action  →  显式 TimeDerivative + AllenCahn + ACInterface
#   ACGrGrPoly(硬编码 mu(η³−η+2γηΣ))  →  AllenCahn 对 F 做符号求导
#   ⇒ 残差在数学上恒等；浮点运算次序不同，预期差 ~1e-12 相对量级，非逐位相同。
#
# 【为什么用 AllenCahn 而不是 MatReaction 补一项】
#   AllenCahn 的雅可比是**符号完备**的（AllenCahn.C:52 对角 ∂²F/∂η²、
#   :65 非对角 ∂²F/∂η∂η_j、ACBulk.h:105 迁移率乘积法则项）。
#   MatReaction 只对**已声明**的参数求导（MatReaction.C:96-109），
#   属于本项目已经栽过一次的那类坑（D 版不收敛的归因之一）。
#
# 【物理：(mu0/4)Ση⁴ 是常数，不是凑数】
#   标准 Landau 展开  f = (a/2)Ση² + (b/4)Ση⁴ + bγΣ_{i<j}η²η_j² 里
#   **温度只进二次项系数 a(T)，四次项系数 b 是常数**。
#   原模型让 mu(T) 同时乘四次项与二次项 —— 这正是 mu<0 时四次项变号、
#   f → −∞ 的根源。本算例取 a = −mu(T)、b = mu0 > 0。
#
# 【网格/参数与对照组完全一致】见 grain_growth_circle.i 的文件头。
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 120
  ny = 120
  xmin = -3.0e-5
  xmax =  3.0e-5
  ymin = -3.0e-5
  ymax =  3.0e-5
  elem_type = QUAD4
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
    type = SmoothCircleIC
    variable = gr0
    x1 = 0
    y1 = 0
    radius = 1.2e-5
    invalue = 1.0
    outvalue = 0.0
    int_width = 2.0e-6
  []
  [gr1_ic]
    type = SmoothCircleIC
    variable = gr1
    x1 = 0
    y1 = 0
    radius = 1.2e-5
    invalue = 0.0
    outvalue = 1.0
    int_width = 2.0e-6
  []
[]

[BCs]
  [Periodic]
    [all]
      auto_direction = 'x y'
    []
  []
[]

[Kernels]
  # --- gr0 ---
  [dgr0dt]
    type = TimeDerivative
    variable = gr0
  []
  [ACBulk0]
    type = AllenCahn
    variable = gr0
    f_name = F
    mob_name = L
    coupled_variables = 'gr1'
  []
  [ACInt0]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
    variable_L = false        # 本算例 L 是常数；∇L = 0，与对照组等价
  []

  # --- gr1 ---
  [dgr1dt]
    type = TimeDerivative
    variable = gr1
  []
  [ACBulk1]
    type = AllenCahn
    variable = gr1
    f_name = F
    mob_name = L
    coupled_variables = 'gr0'
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
  # mu = mu0 = 9.0e5 ⇒ s = 1 ⇒ 与对照组**同一个物理**
  [params]
    type = GenericConstantMaterial
    prop_names  = 'L        kappa_op  gamma_asymm  mu0      mu'
    prop_values = '0.095673 1.8e-6    1.5          9.0e5    9.0e5'
  []

  # 【唯一的自由能】η 方程的全部体自由能都在这里
  #   f = mu0*Σ(η⁴/4) − mu*Σ(η²)/2 + mu0*gamma_asymm*Σ_{i<j} η_i²η_j²
  # mu0 / mu / gamma_asymm 走 material_property_names（不是 coupled_variables）
  # ⇒ F 只耦合 gr0/gr1，AllenCahn 的耦合校验才成立；且 T 相关量不进雅可比。
  [F]
    type = DerivativeParsedMaterial
    property_name = F
    coupled_variables = 'gr0 gr1'
    material_property_names = 'mu0 mu gamma_asymm'
    expression = 'mu0*(gr0^4/4 + gr1^4/4)
                  - mu*(gr0^2 + gr1^2)/2
                  + mu0*gamma_asymm*(gr0^2*gr1^2)'
    derivative_order = 2
  []
[]

[AuxVariables]
  [inside]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [inside]
    type = ParsedAux
    variable = inside
    coupled_variables = 'gr0'
    expression = 'if(gr0>0.5,1,0)'
    execute_on = 'initial timestep_end'
  []
[]

[Postprocessors]
  [area]
    type = ElementIntegralVariablePostprocessor
    variable = inside
    execute_on = 'initial timestep_end'
  []
  [int_gr0]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
    execute_on = 'initial timestep_end'
  []
  [F_grain]
    type = ElementIntegralMaterialProperty
    mat_prop = F
    execute_on = 'timestep_end'
  []
  [gr0_max]
    type = NodalExtremeValue
    variable = gr0
    value_type = max
    execute_on = 'timestep_end'
  []
  [gr1_max]
    type = NodalExtremeValue
    variable = gr1
    value_type = max
    execute_on = 'timestep_end'
  []
  [dt]
    type = TimestepSize
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
  nl_max_its = 50
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-12
  end_time = 6.0e-4
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
    time_step_interval = 50
  []
[]
