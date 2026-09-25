# P1-c: 开域（远场 Dirichlet c=c0）下的 ALPHA 标定
# 界面自 x=0.2um 起以 v=0.1 m/s 扫过静止材料; t_end=1.4e-5 s => 界面到 1.6um
# 判据: 准稳态下界面正前方液相成分 = c_inf/k_e = 0.0571
[Mesh]
  type = GeneratedMesh
  dim = 3
  nx = 1600
  ny = 3
  nz = 2
  xmin = 0.0
  xmax = 8.0000e-06
  ymin = 0.0
  ymax = 6.0000e-07
  zmin = 0.0
  zmax = 6.0000e-07
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
    expression = "0.5*(1-tanh((x-2.0e-7-0.1*t)/(sqrt(2)*2.0e-7)))"
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
    coupled_variables = "c phi"
    constant_names = "k_c c0 A_part"
    constant_expressions = "0.9 0.036 0.264"
    expression = "1.0e9*(k_c/2*(c-c0)^2 + A_part*c^2*(3*phi^2-2*phi^3))"
    derivative_order = 2
  []
  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = "c phi"
    constant_names = "DL DS k_c A_part"
    constant_expressions = "9.5e-9 5.0e-13 0.9 0.264"
    expression = "(DS+(DL-DS)*(1-phi))/(1.0e9*(k_c+2*A_part*(3*phi^2-2*phi^3)))"
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
    coupled_variables = "c phi w"
    constant_names = "A_AT W k_c A_part"
    constant_expressions = "2.04 2.0e-7 0.9 0.264"
    expression = "A_AT*W*2*A_part*(k_c*c + 2*A_part*c*(3*phi^2-2*phi^3))/(k_c*(k_c+2*A_part)) + 0*w"
    derivative_order = 1
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
  [c_p0]
    type = PointValue
    variable = c
    point = "4.000000e-06 0 0"
  []
  [c_p1]
    type = PointValue
    variable = c
    point = "6.000000e-06 0 0"
  []
  [c_p2]
    type = PointValue
    variable = c
    point = "8.000000e-06 0 0"
  []
  [phi_c]
    type = PointValue
    variable = phi
    point = "4.000000e-06 0 0"
  []
  [ptgt]
    type = PointValue
    variable = phi_targ
    point = "4.000000e-06 0 0"
  []
[]

[VectorPostprocessors]
  [line]
    type = LineValueSampler
    variable = 'c phi'
    start_point = '0 0 0'
    end_point = '8.000000e-06 0 0'
    num_points = 400
    sort_by = x
    outputs = lineonly
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 5.0e-8
  end_time = 5.0000e-07
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-9
  l_tol = 1e-10
[]
[Outputs]
  csv = true
  [lineonly]
    type = CSV
    execute_on = FINAL
    file_base = profile
  []
[]
