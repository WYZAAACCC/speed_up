# 【验证】分配系数关系式 k = 1/(1 + 2*A_part/k_c)
#
# 规划 C1 完全依赖这个关系式（用它把 k=0.5 改成真实值），所以必须先数值验证。
#
# 推导：平衡时固液两相化学势 μ = ∂f/∂c 相等
#   液相 (η=0):  f = (k_c/2)(c-c0)^2          => μ_L = k_c(c_L - c0)
#   固相 (η=1):  f = (k_c/2)(c-c0)^2 + A*c^2  => μ_S = k_c(c_S - c0) + 2*A*c_S
#   μ_L = μ_S  =>  k = c_S/c_L = 1/(1 + 2*A/k_c)
#
# 本算例把 η 固定成 tanh 剖面（**不加任何 η 的核**），只让溶质 c 弛豫到平衡，
# 然后在固相深部与液相深部分别取 c 值，与公式对照。
#
# 注意：用**单个**序参量 gr0（tanh 从 1 到 0），于是 Ση^2 = gr0^2 在固相=1、液相=0，
# 与生产算例的 f_loc 形式一致。

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 200
  xmin = 0
  xmax = 1e-6
[]

[Variables]
  [c]
  []
  [w]
  []
[]

[AuxVariables]
  # gr0 做成 AuxVariable 而不是非线性变量：
  #   * MOOSE 要求每个非线性变量至少有一个核，而我们要 gr0 **固定不动**
  #   * AuxVariable 可以被 Material 的 coupled_variables 消费
  #     （生产算例的 grad_Tx / grad_Ty 就是这么用的）
  [gr0]
    order = FIRST
    family = LAGRANGE
  []
[]

[Functions]
  # 【坑】ParsedAux 不认坐标 x；要坐标必须用 ParsedFunction + FunctionAux
  # （生产算例的 gradTx_fn / gradTy_fn 就是这么写的）
  [gr0_fn]
    type = ParsedFunction
    expression = '0.5*(1+tanh((0.5e-6-x)/0.1e-6))'
  []
  # 解析平衡剖面：c_eq(x) = c0*k_c / (k_c + 2*A*g(x)^2)
  #   液相 g=0 -> c = c0   ；固相 g=1 -> c = c0*k
  #   （由 μ = ∂f/∂c 在固液两相相等解出，正是待验证的关系式）
  # 【为什么用它当初值】从均匀浓度出发的弛豫瞬态太刚，A/B 两个变体
  # 会 Solve failed at dtmin。以平衡剖面起步则**无瞬态**，
  # 且若关系式正确，该剖面应保持驻定不动 —— 这本身就是验证。
  [c_eq_fn]
    type = ParsedFunction
    expression = '${c0}*${k_c}/(${k_c} + 2*${A_part}*pow(0.5*(1+tanh((0.5e-6-x)/0.1e-6)),2))'
  []
[]

[AuxKernels]
  # 固相在左（gr0=1），液相在右（gr0=0），界面在 x=0.5e-6
  [gr0_aux]
    type = FunctionAux
    variable = gr0
    function = gr0_fn
    execute_on = 'initial timestep_end'
  []
[]

[ICs]
  [c_ic]
    type = FunctionIC
    variable = c
    function = c_eq_fn
  []
  [w_ic]
    type = ConstantIC
    variable = w
    value = 0
  []
[]

[Kernels]
  # --- 只演化溶质；gr0 没有任何核 => 固定不动 ---
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
  []
[]

[Materials]
  [ch_params]
    type = GenericConstantMaterial
    prop_names = 'M kappa_c'
    prop_values = '1e-6 1e-14'
  []
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '${k_c} ${c0} ${A_part}'
    expression = 'k_c/2*(c-c0)^2 + A_part*c^2*gr0^2'
    derivative_order = 2
  []
[]

[Postprocessors]
  # 固相深部（x≈0.05e-6，单元 10）与液相深部（x≈0.95e-6，单元 190）
  [c_solid]
    type = ElementalVariableValue
    variable = c
    elementid = 10
  []
  [c_liquid]
    type = ElementalVariableValue
    variable = c
    elementid = 190
  []
  [gr0_solid]
    type = ElementalVariableValue
    variable = gr0
    elementid = 10
  []
  [gr0_liquid]
    type = ElementalVariableValue
    variable = gr0
    elementid = 190
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'
  nl_rel_tol = 1e-12
  nl_abs_tol = 1e-14
  nl_max_its = 30
  dt = 1e-6
  end_time = 1.0          # 充分长的相对时间，让溶质弛豫到平衡
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-6
    growth_factor = 2.0
    cutback_factor = 0.5
    optimal_iterations = 8
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
