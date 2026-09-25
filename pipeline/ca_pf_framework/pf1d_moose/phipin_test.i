# 极小测试: 只留 phi 方程, 初值故意错(phi=0), 看能否钉到解析剖面并保持 [0,1]
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 200
  xmin = 0.0
  xmax = 1.0e-6
[]
[Variables]
  [phi]
  []
[]
[AuxVariables]
  [phi_targ]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[ICs]
  [phi_ic]
    type = ConstantIC
    variable = phi
    value = 0.0
  []
[]
[Functions]
  [phi_f]
    type = ParsedFunction
    expression = "0.5*(1-tanh((x-XI0-v*t)/(sqrt(2)*WI)))"
    symbol_names = "XI0 v WI"
    symbol_values = "2.0e-7 0.1 3.0e-8"
  []
[]
[AuxKernels]
  [phi_targ_k]
    type = FunctionAux
    variable = phi_targ
    function = phi_f
  []
[]
[Kernels]
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
[]
[Postprocessors]
  [targ_max]
    type = ElementExtremeValue
    variable = phi_targ
  []
  [targ_min]
    type = ElementExtremeValue
    variable = phi_targ
    value_type = min
  []
  [targ_035]
    type = PointValue
    variable = phi_targ
    point = "3.5e-7 0 0"
  []
  [phi_at_035]
    type = PointValue
    variable = phi
    point = "3.5e-7 0 0"
  []
  [targ_at_035]
    type = PointValue
    variable = phi_targ
    point = "3.5e-7 0 0"
  []
  [phi_max]
    type = NodalExtremeValue
    variable = phi
  []
  [phi_min]
    type = NodalExtremeValue
    variable = phi
    value_type = min
  []
[]
[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 1.0e-8
  end_time = 1.0e-6
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
[]
[Outputs]
  csv = true
[]
