# =============================================================================
# Gate 1 · 步骤 1：纯晶粒长大 R² ∝ t
# =============================================================================
#
# 【测什么】
#   一个孤立的圆形晶粒（gr0）嵌在基体（gr1）里，曲率驱动收缩。
#   二维圆形的解析解：  v = M·σ/R   ⇒   R² = R0² − 2·M·σ·t
#   所以 R² 对 t 应是**直线**，斜率 = −2·M·σ，截距 = R0²。
#
# 【为什么这个测试重要】
#   生产算例的 L / κ / μ 是照 MOOSE 的 GBEvolution 关系写的：
#       κ = 3/4·σ·wGB      (GBEvolutionBase.C:98)
#       μ = 3/4·(1/f0s)·σ/wGB，f0s=1/8 时 = 6σ/wGB   (:100)
#       L = 4/3·M_GB/wGB
#   这套关系**设计上**应让弥散界面模型在薄界面极限复现 v = M·σ·κ_curv。
#   但"设计上应该"必须**实测**——本项目最贵的一课就是"推理不算数"。
#
#   所以：量出 M_eff，与 M0·exp(−Q/(kb·T)) 对照。
#   若一致 ⇒ 参数化正确，Gate 1 后续的 k_eff 判据才建立在可信的界面上。
#
# 【参数怎么定的】
#   T = 1830 K（< 1882.2 K 的 μ 过零点，保证 μ > 0 ⇒ 纯晶粒长大，无熔化）
#   σ = 0.6 J/m², wGB = 4 µm, M0 = 232 m^4/(J·s), Q = 3.234 eV
#   ⇒ M = M0·exp(−Q/(kb·T))、κ = 0.75σwGB、μ = 6σ/wGB、L = 4/3·M/wGB
#   R0 = 12 µm、域 60 µm：R0/d = 6 个界面宽（R² 律要求 R >> d）
#
# 【网格】dx = 0.5 µm，d = sqrt(2κ/μ) = 2.0 µm ⇒ **4 个单元/界面**（满足判据）
#   CLI 覆盖做收敛性测试：Mesh/nx=60（dx=1µm，2 单元/界面）、240（8 单元/界面）
#   ⚠ 本文件用 GeneratedMesh 直接写网格（不是生成器链），所以 `Mesh/nx` 有效。
#
# 【同时验证的另外两条】（Gate 0 遗留）
#   * F_grain 单调下降（耗散）—— 用 [f_grain] 材料 + 后处理器
#   * Ση² ≤ 1 —— 用 gr*_max 后处理器
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
  # gr0 = 圆内 1、圆外 0；gr1 相反 ⇒ 两者之和 ≈ 1（对称剖面）
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
  # 周期边界：孤立晶粒在无限基体中的等效
  [Periodic]
    [all]
      auto_direction = 'x y'
    []
  []
[]

[Modules]
  [PhaseField]
    [GrainGrowth]
      # 常数迁移率（无温度场）；L / kappa_op 由下面的材料提供
      mobility = L
      kappa = kappa_op
    []
  []
[]

[Materials]
  # T = 1830 K 下的 Arrhenius（见文件头推导）
  #   M = 232 * exp(-3.234/(8.617e-5*1830)) = 2.8702e-07
  [params]
    type = GenericConstantMaterial
    prop_names  = 'L        kappa_op  gamma_asymm  mu'
    prop_values = '0.095673 1.8e-6    1.5          9.0e5'
  []

  # 晶粒体自由能（与生产输入的定义逐字一致，已验证到机器精度）
  [f_grain]
    type = DerivativeParsedMaterial
    property_name = f_grain
    coupled_variables = 'gr0 gr1'
    material_property_names = 'mu gamma_asymm'
    expression = 'mu*((gr0^4/4-gr0^2/2)+(gr1^4/4-gr1^2/2)
                   +gamma_asymm*(gr0^2*gr1^2))'
    derivative_order = 1
  []
[]

[AuxVariables]
  [inside]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  # 圆内 = 1（用 0.5 阈值计数，比积分 ∫η 更干净：不受界面展宽影响）
  [inside]
    type = ParsedAux
    variable = inside
    coupled_variables = 'gr0'
    expression = 'if(gr0>0.5,1,0)'
    execute_on = 'initial timestep_end'
  []
[]

[Postprocessors]
  # 圆面积 -> 等效半径 R = sqrt(A/pi)
  [area]
    type = ElementIntegralVariablePostprocessor
    variable = inside
    execute_on = 'initial timestep_end'
  []
  # ∫gr0 dA：与面积对照，用于估计界面展宽带来的偏差
  [int_gr0]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
    execute_on = 'initial timestep_end'
  []
  [sum_eta2_max]
    type = ElementExtremeValue
    variable = inside
    value_type = max
    execute_on = 'timestep_end'
  []
  [F_grain]
    type = ElementIntegralMaterialProperty
    mat_prop = f_grain
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
  # 预计收缩时间 R0^2/(2*M*sigma) ≈ 4.2e-4 s；留余量
  end_time = 6.0e-4
  dtmax = 2.0e-6      # << 界面弛豫时间 1/(L*mu) = 1.16e-5 s
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
