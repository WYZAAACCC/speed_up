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
  [fv]
    family = MONOMIAL
    order = CONSTANT
  []
  [dfv]
    family = MONOMIAL
    order = CONSTANT
  []
  [d2fv]
    family = MONOMIAL
    order = CONSTANT
  []
[]
[AuxKernels]
  [fv_a]
    type = MaterialRealAux
    variable = fv
    property = ftest
    execute_on = initial
  []
  [dfv_a]
    type = MaterialRealAux
    variable = dfv
    property = "dftest/dc"
    execute_on = initial
  []
  [d2fv_a]
    type = MaterialRealAux
    variable = d2fv
    property = "d^2ftest/dc^2"
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
  [mt]
    type = DerivativeParsedMaterial
    property_name = ftest
    coupled_variables = "c"
    constant_names = "C1 AA BB"
    constant_expressions = "1e-3 7.0 -0.00790679"
    expression = "if(c<C1, AA*(c-C1)+BB, c*log(c))"
    derivative_order = 2
  []
[]
[Postprocessors]
  [vv]
    type = ElementAverageValue
    variable = fv
    execute_on = initial
  []
  [dv]
    type = ElementAverageValue
    variable = dfv
    execute_on = initial
  []
  [ddv]
    type = ElementAverageValue
    variable = d2fv
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
  file_base = iftest
[]
