# P1-c: 界面扫过静止材料, 但 phi 是【真正的 Variable】(不再是 AuxVariable)
#   => d(phi)/dt != 0 => AntitrappingCurrent 不再恒为零
# phi 用罚项钉到目标剖面 (Reaction + CoupledForce), 从而可以规定界面速度。

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 1000
  xmin = 0.0
  xmax = 1.0e-6
[]

[Variables]
  [c]
  []
  [w]
  []
  [phi]
  []
[]

[AuxVariables]
  [phi_targ]
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
  [phi_ic]
    type = FunctionIC
    variable = phi
    function = phi_f
  []
[]

[Functions]
  [phi_f]
    type = ParsedFunction
    expression = "0.5*(1-tanh((x-XI0-v*t)/(sqrt(2)*WI)))"
    symbol_names = "XI0 v WI"
    symbol_values = "2.0e-7 0.1 3.0e-8"
  []
  [T_f]
    type = ParsedFunction
    expression = "TLI + G*(x-XI0-v*t)"
    symbol_names = "TLI G XI0 v"
    symbol_values = "1911.1 5e6 2.0e-7 0.1"
  []
[]

[AuxKernels]
  [phi_targ_k]
    type = FunctionAux
    variable = phi_targ
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
  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = "c phi"
    constant_names = "ALPHA W k_eq"
    constant_expressions = "2.0 3.0e-8 0.6303"
    expression = "ALPHA*W*(1-k_eq)*c*(1-phi)"
    derivative_order = 2
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
  [phi_dt]
    type = CoefTimeDerivative
    variable = phi
    Coefficient = 1.0e-9
  []
  [pin_a]
    type = Reaction
    variable = phi
  []
  [pin_b]
    type = CoupledForce
    variable = phi
    v = phi_targ
    coef = 1.0
  []
  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = phi
    f_name = F_at
    coupled_variables = "c phi"
  []
[]

[Postprocessors]
  [c_ahead]
    type = PointValue
    variable = c
    point = "4.0e-7 0 0"
  []
  [c_behind]
    type = PointValue
    variable = c
    point = "5.0e-8 0 0"
  []
  [c_far]
    type = PointValue
    variable = c
    point = "9.8e-7 0 0"
  []
  [phi_mid_err]
    type = PointValue
    variable = phi
    point = "6.0e-7 0 0"
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 2.0e-8
  end_time = 6.0e-6
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-9
  l_tol = 1e-10
[]

[Outputs]
  csv = true
[]
