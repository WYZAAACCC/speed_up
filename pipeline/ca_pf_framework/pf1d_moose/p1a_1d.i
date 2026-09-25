# P1-a（1D 稳态界面匹配的第一步）: 冻结 phi + 均匀 T, 验证两相共存给出 c_s/c_l = k_e
# 结构完全照抄 pipeline/stage1_meltpool_c.i 的分裂 CH 写法（w = 分裂化学势）。
# 自由能: f = R*T/Vm*[(1-c)ln(1-c)+c*ln c] + h(phi)*(dgB + dHf*(1-T/Tm))*c/Vm
#   => df/dc = (R*T/Vm)*ln(c/(1-c)) + h(phi)*(dgB + dHf*(1-T/Tm))/Vm   (自动是插值化学势)
#   dgB = 7334 J/mol 由【液相线对】(c_l=c0, c_s=k_e*c0, T=TL) 自洽定出。

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 400
  xmin = -2.0e-7
  xmax = 2.0e-7
[]

[Variables]
  [c]
  []
  [w]
  []
[]

[AuxVariables]
  [phi]
    order = CONSTANT
    family = MONOMIAL
  []
  [T]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[ICs]
  [c_ic]
    type = ConstantIC
    variable = c
    value = 0.036
  []
[]

[Functions]
  [phi_f]
    type = ParsedFunction
    expression = "0.5*(1-tanh(x/(sqrt(2)*WI)))"
    symbol_names = WI
    symbol_values = 2.0e-8
  []
  [T_f]
    type = ParsedFunction
    expression = "TLI"
    symbol_names = TLI
    symbol_values = 1911.1
  []
[]

[AuxKernels]
  [phi_k]
    type = FunctionAux
    variable = phi
    function = phi_f
  []
  [T_k]
    type = FunctionAux
    variable = T
    function = T_f
  []
[]

[Materials]
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = "c phi T"
    expression = "R*T/Vm*((1-c)*log(1-c)+c*log(c)) + (3*phi^2-2*phi^3)*(dgB+dHf*(1-T/Tm))*c/Vm"
    constant_names = "R Vm dgB dHf Tm"
    constant_expressions = "8.314 1.1345e-5 7334 14150 1941"
    derivative_order = 2
  []
  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = "c T"
    expression = "DL*Vm*c*(1-c)/(R*T)"
    constant_names = "DL R Vm"
    constant_expressions = "9.5e-9 8.314 1.1345e-5"
    derivative_order = 1
  []
  [kappa_c]
    type = GenericConstantMaterial
    prop_names = kappa_c
    prop_values = 0.0
  []
[]

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
    coupled_variables = "phi"
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
    coupled_variables = "phi T"
  []
[]

[Postprocessors]
  [c_solid_far]
    type = PointValue
    variable = c
    point = "-1.5e-7 0 0"
  []
  [c_liquid_far]
    type = PointValue
    variable = c
    point = "1.5e-7 0 0"
  []
  [cmax]
    type = NodalExtremeValue
    variable = c
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 1.0e-6
  end_time = 3.0e-3
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-10
  l_tol = 1e-10
[]

[Outputs]
  csv = true
  exodus = false
[]

[Debug]
  show_var_residual_norms = true
[]
