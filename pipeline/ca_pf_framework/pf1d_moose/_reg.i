# P1-c: 开域（远场 Dirichlet c=c0）下的 ALPHA 标定
# 界面自 x=0.2um 起以 v=0.1 m/s 扫过静止材料; t_end=1.4e-5 s => 界面到 1.6um
# 判据: 准稳态下界面正前方液相成分 = c_inf/k_e = 0.0571
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 1600
  xmin = 0.0
  xmax = 8.0000e-06
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
    coupled_variables = "c phi T"
    constant_names = "R Vm dgB dHf Tm C1 C2 G1 GP1 GPP1 G2 GP2 GPP2"
    constant_expressions = "8.314 1.1345e-5 7334 14150 1941 1.0000000000e-03 9.5000000000e-01 -7.9072551122e-03 -6.9067547786e+00 1.0010010010e+03 -1.9851524335e-01 2.9444389792e+00 2.1052631579e+01"
    expression = "R*T/Vm*(if(c<C1, G1+GP1*(c-C1)+0.5*GPP1*(c-C1)^2, if(c>C2, G2+GP2*(c-C2)+0.5*GPP2*(c-C2)^2, c*log(c)+(1-c)*log(1-c)))) + (3*phi^2-2*phi^3)*(dgB+dHf*(1-T/Tm))*c/Vm"
    derivative_order = 2
  []
  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = "c phi T"
    constant_names = "DL DS R Vm C1 C2 GPP1 GPP2"
    constant_expressions = "9.5e-9 5.0e-13 8.314 1.1345e-5 1.0000000000e-03 9.5000000000e-01 1.0010010010e+03 2.1052631579e+01"
    expression = "(DS+(DL-DS)*(1-phi))*Vm/(R*T*(if(c<C1, GPP1, if(c>C2, GPP2, 1/c+1/(1-c)))))"
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
    coupled_variables = "c phi T w"
    constant_names = "A_AT W R dgB dHf Tm"
    constant_expressions = "2.04 2.0e-7 8.314 7334 14150 1941"
    expression = "A_AT*W*((1/(1+((1-c)/c)*exp(-(3*phi^2-2*phi^3)*(dgB+dHf*(1-T/Tm))/(R*T))))-(1/(1+((1-c)/c)*exp((1-(3*phi^2-2*phi^3))*(dgB+dHf*(1-T/Tm))/(R*T))))) + 0*w"
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
    coupled_variables = "c phi T"
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
  end_time = 5.0000e-05
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
