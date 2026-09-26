[Tests]
[]
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 1
  xmin = 0
  xmax = 1
[]
[Variables]
  [c]
  []
[]
[ICs]
  [c_ic]
    type = ConstantIC
    variable = c
    value = 0.036
  []
[]
[AuxVariables]
  [fl]
  []
  [dfl]
  []
  [d2fl]
  []
[]
[AuxKernels]
  [fl_a]
    type = MaterialRealAux
    variable = fl
    property = f_loc
    execute_on = initial
  []
  [dfl_a]
    type = MaterialRealAux
    variable = dfl
    property = "d(f_loc)/dc"
    execute_on = initial
  []
  [d2fl_a]
    type = MaterialRealAux
    variable = d2fl
    property = "d2(f_loc)/dc2"
    execute_on = initial
  []
[]
[Kernels]
  [td]
    type = TimeDerivative
    variable = c
  []
[]
[Materials]
  [fe]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = "c"
    constant_names = "FREF CFLOOR"
    constant_expressions = "1.6423e9 1e-6"
    expression = "FREF*( max(c,CFLOOR)*log(max(c,CFLOOR)) )"
    derivative_order = 2
  []
[]
[Postprocessors]
  [flv]
    type = ElementAverageValue
    variable = fl
    execute_on = initial
  []
  [dflv]
    type = ElementAverageValue
    variable = dfl
    execute_on = initial
  []
  [d2flv]
    type = ElementAverageValue
    variable = d2fl
    execute_on = initial
  []
[]
[Executioner]
  type = Transient
  end_time = 1
  dt = 1
[]
[Outputs]
  csv = true
[]
