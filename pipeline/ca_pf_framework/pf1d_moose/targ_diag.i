[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 200
  xmin = 0.0
  xmax = 1.0e-6
[]
[Variables]
  [u]
  []
[]
[AuxVariables]
  [phi_targ]
    order = CONSTANT
    family = MONOMIAL
  []
  [phi_targ2]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[ICs]
  [u_ic]
    type = ConstantIC
    variable = u
    value = 0.0
  []
[]
[Functions]
  [f_hard]
    type = ParsedFunction
    expression = "0.5*(1-tanh((x-2e-7-0.1*t)/(sqrt(2)*3e-8)))"
  []
  [f_sym]
    type = ParsedFunction
    expression = "0.5*(1-tanh((x-XS-vv*t)/(sqrt(2)*WS)))"
    symbol_names = "XS vv WS"
    symbol_values = "2e-7 0.1 3e-8"
  []
[]
[AuxKernels]
  [t1]
    type = FunctionAux
    variable = phi_targ
    function = f_hard
  []
  [t2]
    type = FunctionAux
    variable = phi_targ2
    function = f_sym
  []
[]
[Kernels]
  [u_dt]
    type = TimeDerivative
    variable = u
  []
[]

[Postprocessors]
  [hard_max]
    type = ElementExtremeValue
    variable = phi_targ
  []
  [hard_min]
    type = ElementExtremeValue
    variable = phi_targ
    value_type = min
  []
  [sym_max]
    type = ElementExtremeValue
    variable = phi_targ2
  []
  [sym_min]
    type = ElementExtremeValue
    variable = phi_targ2
    value_type = min
  []
  [hard_at_035]
    type = PointValue
    variable = phi_targ
    point = "3.5e-7 0 0"
  []
  [sym_at_035]
    type = PointValue
    variable = phi_targ2
    point = "3.5e-7 0 0"
  []
  [hard_at_030]
    type = PointValue
    variable = phi_targ
    point = "3.0e-7 0 0"
  []
[]
[Executioner]
  type = Transient
  dt = 1.0e-7
  end_time = 1.0e-6
[]
[Outputs]
  csv = true
[]
