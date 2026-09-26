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
  [fr]
    family = MONOMIAL
    order = CONSTANT
  []
  [dfr]
    family = MONOMIAL
    order = CONSTANT
  []
  [d2fr]
    family = MONOMIAL
    order = CONSTANT
  []
  [di]
    family = MONOMIAL
    order = CONSTANT
  []
  [ddi]
    family = MONOMIAL
    order = CONSTANT
  []
  [d2di]
    family = MONOMIAL
    order = CONSTANT
  []
[]
[AuxKernels]
  [k_fr]
    type = MaterialRealAux
    variable = fr
    property = "f_reg"
    execute_on = initial
  []
  [k_dfr]
    type = MaterialRealAux
    variable = dfr
    property = "df_reg/dc"
    execute_on = initial
  []
  [k_d2fr]
    type = MaterialRealAux
    variable = d2fr
    property = "d^2f_reg/dc^2"
    execute_on = initial
  []
  [k_di]
    type = MaterialRealAux
    variable = di
    property = "f_id"
    execute_on = initial
  []
  [k_ddi]
    type = MaterialRealAux
    variable = ddi
    property = "df_id/dc"
    execute_on = initial
  []
  [k_d2di]
    type = MaterialRealAux
    variable = d2di
    property = "d^2f_id/dc^2"
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
  [m_reg]
    type = DerivativeParsedMaterial
    property_name = f_reg
    coupled_variables = "c"
    constant_names = "FREF C1 C2 G1 GP1 GPP1 G2 GP2 GPP2"
    constant_expressions = "1.6423000000e+09 1.0000000000e-03 9.0000000000e-01 -7.9072551122e-03 -6.9067547786e+00 1.0010010010e+03 -3.2508297339e-01 2.1972245773e+00 1.1111111111e+01"
    expression = "FREF*(if(c<C1, G1+GP1*(c-C1)+0.5*GPP1*(c-C1)^2, if(c>C2, G2+GP2*(c-C2)+0.5*GPP2*(c-C2)^2, c*log(c)+(1-c)*log(1-c))))"
    derivative_order = 2
  []
  [m_id]
    type = DerivativeParsedMaterial
    property_name = f_id
    coupled_variables = "c"
    constant_names = "FREF"
    constant_expressions = "1.6423000000e+09"
    expression = "FREF*(c*log(c)+(1-c)*log(1-c))"
    derivative_order = 2
  []
[]
[Postprocessors]
  [p_fr]
    type = ElementAverageValue
    variable = fr
    execute_on = initial
  []
  [p_dfr]
    type = ElementAverageValue
    variable = dfr
    execute_on = initial
  []
  [p_d2fr]
    type = ElementAverageValue
    variable = d2fr
    execute_on = initial
  []
  [p_di]
    type = ElementAverageValue
    variable = di
    execute_on = initial
  []
  [p_ddi]
    type = ElementAverageValue
    variable = ddi
    execute_on = initial
  []
  [p_d2di]
    type = ElementAverageValue
    variable = d2di
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
  file_base = reg
[]
