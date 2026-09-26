# 正对照：ScaledCoupledTimeDerivative 的功能验证
# 退化算例：c 方程里 w = df/dc 用 f = (1/2)c^2 => w = c；w 方程 = scale*dc/dt + div(M grad w)
# 取 scale = 2、M = 1 => 实际是 2*dc/dt = lap(c)  => 有效扩散系数 = 0.5
# 对照：scale = 1 时有效扩散系数 = 1
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 1
    nx = 100
    xmin = 0
    xmax = 1
  []
[]
[Variables]
  [c]
  []
  [w]
    initial_condition = 0.0
  []
[]
[ICs]
  [c_ic]
    type = FunctionIC
    variable = c
    function = ic_fn
  []
[]
[Functions]
  [ic_fn]
    type = ParsedFunction
    expression = '0.5*sin(pi*x)'
  []
[]
[Kernels]
  [w_dt]
    type = ScaledCoupledTimeDerivative
    variable = w
    v = c
    scale = cap
  []
  [w_res]
    type = MatDiffusion
    variable = w
    diffusivity = Dconst
  []
  [c_parsed]
    type = MatReaction
    variable = c
    reaction_rate = one
  []
  [c_w]
    type = CoupledForce
    variable = c
    v = w
  []
[]
[Materials]
  [consts]
    type = GenericConstantMaterial
    prop_names = 'Dconst one'
    prop_values = '1.0 1.0'
  []
  [cap]
    type = DerivativeParsedMaterial
    property_name = cap
    coupled_variables = 'c'
    constant_names = 'SCALE'
    constant_expressions = '@SCALE@'
    expression = 'SCALE + 0*c'
    derivative_order = 1
  []
[]
[Postprocessors]
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
  []
[]
[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
  nl_rel_tol = 1e-12
  nl_abs_tol = 1e-14
  dt = 1e-4
  end_time = 2e-3
[]
[Outputs]
  csv = true
  print_linear_residuals = false
[]