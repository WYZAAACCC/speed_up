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
    value = 0.1
  []
[]
[AuxVariables]
  [fA]
    family = MONOMIAL
    order = CONSTANT
  []
  [dA]
    family = MONOMIAL
    order = CONSTANT
  []
  [fB]
    family = MONOMIAL
    order = CONSTANT
  []
  [dB]
    family = MONOMIAL
    order = CONSTANT
  []
  [fC]
    family = MONOMIAL
    order = CONSTANT
  []
  [dC]
    family = MONOMIAL
    order = CONSTANT
  []
[]
[AuxKernels]
  [kA]
    type = MaterialRealAux
    variable = fA
    property = m_min
    execute_on = initial
  []
  [kA2]
    type = MaterialRealAux
    variable = dA
    property = "dm_min/dc"
    execute_on = initial
  []
  [kB]
    type = MaterialRealAux
    variable = fB
    property = m_max
    execute_on = initial
  []
  [kB2]
    type = MaterialRealAux
    variable = dB
    property = "dm_max/dc"
    execute_on = initial
  []
  [kC]
    type = MaterialRealAux
    variable = fC
    property = m_if
    execute_on = initial
  []
  [kC2]
    type = MaterialRealAux
    variable = dC
    property = "dm_if/dc"
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
  [mA]
    type = DerivativeParsedMaterial
    property_name = m_min
    coupled_variables = "c"
    expression = "min(1, 2*c) + c*c"
    derivative_order = 1
  []
  [mB]
    type = DerivativeParsedMaterial
    property_name = m_max
    coupled_variables = "c"
    expression = "max(c, 0.5) + c*c"
    derivative_order = 1
  []
  [mC]
    type = DerivativeParsedMaterial
    property_name = m_if
    coupled_variables = "c"
    expression = "if(c<0.5, 2*c, 1) + c*c"
    derivative_order = 1
  []
[]
[Postprocessors]
  [pA]
    type = ElementAverageValue
    variable = fA
    execute_on = initial
  []
  [pA2]
    type = ElementAverageValue
    variable = dA
    execute_on = initial
  []
  [pB]
    type = ElementAverageValue
    variable = fB
    execute_on = initial
  []
  [pB2]
    type = ElementAverageValue
    variable = dB
    execute_on = initial
  []
  [pC]
    type = ElementAverageValue
    variable = fC
    execute_on = initial
  []
  [pC2]
    type = ElementAverageValue
    variable = dC
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
  file_base = mm
[]
