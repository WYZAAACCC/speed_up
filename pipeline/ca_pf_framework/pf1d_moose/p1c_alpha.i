# P1-c: 开域（远场 Dirichlet c=c0）下的 ALPHA 标定
# 界面自 x=0.2um 起以 v=0.1 m/s 扫过静止材料; t_end=1.4e-5 s => 界面到 1.6um
# 判据: 准稳态下界面正前方液相成分 = c_inf/k_e = 0.0571
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 1200
  xmin = 0.0
  xmax = 2.4e-6
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
    expression = "0.5*(1-tanh((x-2.0e-7-0.1*t)/(sqrt(2)*3.0e-8)))"
  []
  [T_f]
    type = ParsedFunction
    expression = "1911.1 + 5.0e6*(x-2.0e-7-0.1*t)"
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
    constant_expressions = "3.0 3.0e-8 0.6303"
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
[BCs]
  [c_far]
    type = DirichletBC
    variable = c
    boundary = right
    value = 0.036
  []
[]
[Postprocessors]
  [c_1700]
    type = PointValue
    variable = c
    point = "1.70e-6 0 0"
  []
  [c_1750]
    type = PointValue
    variable = c
    point = "1.75e-6 0 0"
  []
  [c_1800]
    type = PointValue
    variable = c
    point = "1.80e-6 0 0"
  []
  [c_2000]
    type = PointValue
    variable = c
    point = "2.00e-6 0 0"
  []
[]
[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 5.0e-8
  end_time = 1.4e-5
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-9
  l_tol = 1e-10
[]
[Outputs]
  csv = true
[]
