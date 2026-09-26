# 探针 2：只用 log()，确认它是自然对数（c=0.25 时 ln=-1.386294, log10=-0.602060）
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 1
    nx = 2
    xmin = 0
    xmax = 1
  []
[]
[Variables]
  [c]
    initial_condition = 0.25
  []
[]
[Kernels]
  [dt]   type = TimeDerivative variable = c []
  [diff] type = Diffusion      variable = c []
[]
[AuxVariables]
  [v_log]  order = CONSTANT family = MONOMIAL []
  [v_mix]  order = CONSTANT family = MONOMIAL []
  [v_d2]   order = CONSTANT family = MONOMIAL []
[]
[AuxKernels]
  [a_log] type = MaterialRealAux variable = v_log property = p_log execute_on = 'initial timestep_end' []
  [a_mix] type = MaterialRealAux variable = v_mix property = p_mix execute_on = 'initial timestep_end' []
  [a_d2]  type = MaterialRealAux variable = v_d2  property = p_d2  execute_on = 'initial timestep_end' []
[]
[Materials]
  [m_log]
    type = DerivativeParsedMaterial
    property_name = p_log
    coupled_variables = 'c'
    expression = 'log(c)'
    derivative_order = 1
  []
  # 理想溶液混合自由能的无量纲形式： c*ln c + (1-c)*ln(1-c)
  [m_mix]
    type = DerivativeParsedMaterial
    property_name = p_mix
    coupled_variables = 'c'
    expression = 'c*log(c) + (1-c)*log(1-c)'
    derivative_order = 2
  []
  # 二阶导： 1/c + 1/(1-c) = 1/(c(1-c))
  [m_d2]
    type = DerivativeParsedMaterial
    property_name = p_d2
    coupled_variables = 'c'
    expression = '1/c + 1/(1-c)'
    derivative_order = 2
  []
[]
[Postprocessors]
  [c_val]   type = ElementAverageValue variable = c     []
  [log_val] type = ElementAverageValue variable = v_log []
  [mix_val] type = ElementAverageValue variable = v_mix []
  [d2_val]  type = ElementAverageValue variable = v_d2  []
[]
[Executioner]
  type = Transient
  end_time = 1e-9
  dt = 1e-9
  solve_type = NEWTON
[]
[Outputs]
  csv = true
  print_linear_residuals = false
[]