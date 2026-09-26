# =============================================================================
# 3 晶粒 Mercedes 构型：把 Gibbs 面接进**真实演化的相场**（第 1 关）
# =============================================================================
# 构型：三个 Voronoi 胞 = Mercedes 星（三条晶界在中心以 120 相交）
#       ⇒ **对称平衡态** ⇒ 三条晶界应静止不动
# 关键：η 的 IC 与共形低维面块用**同一套 Voronoi 种子与度规** ⇒ 按构造重合
#
# 检查项（用户要求的三条）：
#   T1 拓扑是否正确  —— h_gb 的峰值是否落在共形 sideset 上
#   T2 晶界是否稳定  —— 相场演化中晶界是否移动（对称构型应不动）
#   T3 多晶界是否闭合 —— 三条晶界交汇于一点，各自晶粒边界闭合
# =============================================================================
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 80
    ny = 80
    xmin = 0
    xmax = 2.0e-08
    ymin = 0
    ymax = 2.0e-08
    elem_type = QUAD4
  []
  # --- Mercedes = 3 个 Voronoi 胞（种子在正三角形顶点）---
  # 种子: s0=(10,14), s1=(6.536,8), s2=(13.464,8)  单位 nm
  [g1]
    type = ParsedSubdomainMeshGenerator
    input = gen
    block_id = 1
    combinatorial_geometry = '(((x-6.536e-9)^2+(y-8e-9)^2 < (x-1.0e-8)^2+(y-1.4e-8)^2) & ((x-6.536e-9)^2+(y-8e-9)^2 < (x-1.3464e-8)^2+(y-8e-9)^2))'
  []
  [g2]
    type = ParsedSubdomainMeshGenerator
    input = g1
    block_id = 2
    combinatorial_geometry = '(((x-1.3464e-8)^2+(y-8e-9)^2 < (x-1.0e-8)^2+(y-1.4e-8)^2) & ((x-1.3464e-8)^2+(y-8e-9)^2 < (x-6.536e-9)^2+(y-8e-9)^2))'
  []
  # --- 三条晶界的共形 sideset（块间界面 = 晶界）---
  [ib01]
    type = SideSetsBetweenSubdomainsGenerator
    input = g2
    primary_block = 0
    paired_block = 1
    new_boundary = gb01
  []
  [ib12]
    type = SideSetsBetweenSubdomainsGenerator
    input = ib01
    primary_block = 1
    paired_block = 2
    new_boundary = gb12
  []
  [ib20]
    type = SideSetsBetweenSubdomainsGenerator
    input = ib12
    primary_block = 2
    paired_block = 0
    new_boundary = gb20
  []
[]


[Variables]
  # 显式声明（不用 PolycrystalVariables action —— 它会覆盖我的 FunctionIC）
  [gr0]
  []
  [gr1]
  []
  [gr2]
  []
[]

[ICs]
  # η 的初值用**同一套 Voronoi 条件** ⇒ 与块结构一致
  [gr0_ic]
    type = FunctionIC
    variable = gr0
    function = g0_fn
  []
  [gr1_ic]
    type = FunctionIC
    variable = gr1
    function = g1_fn
  []
  [gr2_ic]
    type = FunctionIC
    variable = gr2
    function = g2_fn
  []
[]

[Functions]
  [g0_fn]
    type = ParsedFunction
    expression = 'exp(-max(0,((x-1.0e-8)^2+(y-1.4e-8)^2)-((x-6.536e-9)^2+(y-8e-9)^2))/4.0e-18 - max(0,((x-1.0e-8)^2+(y-1.4e-8)^2)-((x-1.3464e-8)^2+(y-8e-9)^2))/4.0e-18)'
  []
  [g1_fn]
    type = ParsedFunction
    expression = 'exp(-max(0,((x-6.536e-9)^2+(y-8e-9)^2)-((x-1.0e-8)^2+(y-1.4e-8)^2))/4.0e-18 - max(0,((x-6.536e-9)^2+(y-8e-9)^2)-((x-1.3464e-8)^2+(y-8e-9)^2))/4.0e-18)'
  []
  [g2_fn]
    type = ParsedFunction
    expression = 'exp(-max(0,((x-1.3464e-8)^2+(y-8e-9)^2)-((x-1.0e-8)^2+(y-1.4e-8)^2))/4.0e-18 - max(0,((x-1.3464e-8)^2+(y-8e-9)^2)-((x-6.536e-9)^2+(y-8e-9)^2))/4.0e-18)'
  []
[]

[AuxVariables]
  # 晶界指示 8(S^2-Q)：峰值线 = 真实晶界位置
  [hgb]
    order = CONSTANT
    family = MONOMIAL
  []
  [Saux]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [hgb_k]
    type = ParsedAux
    variable = hgb
    coupled_variables = 'gr0 gr1 gr2'
    expression = '8*((gr0^2+gr1^2+gr2^2)^2 - (gr0^4+gr1^4+gr2^4))'
    execute_on = 'initial timestep_end'
  []
  [S_k]
    type = ParsedAux
    variable = Saux
    coupled_variables = 'gr0 gr1 gr2'
    expression = 'gr0^2+gr1^2+gr2^2'
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  # 相场晶粒长大：ACInterface + ACGrGrPoly（手写，不用 action，便于控制）
  [gr0_iface]
    type = ACInterface
    variable = gr0
    kappa_name = kappa_op
    mob_name = L
  []
  [gr0_poly]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr1 gr2'
  []
  [gr1_iface]
    type = ACInterface
    variable = gr1
    kappa_name = kappa_op
    mob_name = L
  []
  [gr1_poly]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0 gr2'
  []
  [gr2_iface]
    type = ACInterface
    variable = gr2
    kappa_name = kappa_op
    mob_name = L
  []
  [gr2_poly]
    type = ACGrGrPoly
    variable = gr2
    v = 'gr0 gr1'
  []
[]

[Materials]
  [kappa_op]
    type = DerivativeParsedMaterial
    property_name = kappa_op
    coupled_variables = 'gr0 gr1 gr2'
    constant_names = 'K0'
    constant_expressions = '5.0e-13'
    expression = 'K0 + 0*(gr0+gr1+gr2)'
    derivative_order = 2
  []
  [L]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'gr0 gr1 gr2'
    constant_names = 'L0'
    constant_expressions = '0.6667'
    expression = 'L0 + 0*(gr0+gr1+gr2)'
    derivative_order = 2
  []
  [mu]
    type = DerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'gr0 gr1 gr2'
    constant_names = 'MU0'
    constant_expressions = '1.0e6'
    expression = 'MU0 + 0*(gr0+gr1+gr2)'
    derivative_order = 2
  []
  [gamma_asymm]
    type = DerivativeParsedMaterial
    property_name = gamma_asymm
    coupled_variables = 'gr0 gr1 gr2'
    constant_names = 'G0'
    constant_expressions = '1.5'
    expression = 'G0 + 0*(gr0+gr1+gr2)'
    derivative_order = 2
  []
[]

[Postprocessors]
  # T2 稳定性：∫h_gb dV 应恒定（晶界网络不动）
  [hgb_int]
    type = ElementIntegralVariablePostprocessor
    variable = hgb
    execute_on = 'initial timestep_end'
  []
  # 三个晶粒的面积分数应守恒（总量守恒 + 对称 ⇒ 各自不变）
  [gr0_int]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
    execute_on = 'initial timestep_end'
  []
  [gr1_int]
    type = ElementIntegralVariablePostprocessor
    variable = gr1
    execute_on = 'initial timestep_end'
  []
  [gr2_int]
    type = ElementIntegralVariablePostprocessor
    variable = gr2
    execute_on = 'initial timestep_end'
  []
  [S_max]
    type = ElementExtremeValue
    variable = Saux
    value_type = max
    execute_on = 'timestep_end'
  []
  [S_min]
    type = ElementExtremeValue
    variable = Saux
    value_type = min
    execute_on = 'timestep_end'
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-14`n  nl_max_its = 50
  dt = 1.0e-6
  end_time = 1.0e-4
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.0e-6
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]