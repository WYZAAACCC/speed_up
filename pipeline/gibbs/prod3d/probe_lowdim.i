# 探针：无 block 限制的变量 / 核，会不会跑到低维块上去
# 目的：决定把 Gibbs 面接进生产输入时，是否必须给每个变量/核/材料加 block
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 4
    ny = 2
    xmax = 4
    ymax = 2
  []
  [left]
    type = SubdomainBoundingBoxGenerator
    input = gen
    block_id = 1
    block_name = left
    bottom_left = '0 0 0'
    top_right = '2 2 0'
  []
  [gb]
    type = SideSetsBetweenSubdomainsGenerator
    input = left
    primary_block = 0
    paired_block = 1
    new_boundary = gb
  []
  [gbb]
    type = LowerDBlockFromSidesetGenerator
    input = gb
    sidesets = 'gb'
    new_block_id = 2
    new_block_name = gbb
  []
[]

[Variables]
  # u 故意**不加 block 限制**
  [u]
  []
  [lam]
    block = 2
    initial_condition = 2
  []
[]

[ICs]
  [u_ic]
    type = FunctionIC
    variable = u
    function = u_fn
  []
[]

[Functions]
  [u_fn]
    type = ParsedFunction
    expression = '1 + 0.3*sin(2*x)'
  []
[]

[Kernels]
  # 故意不加 block
  [u_dt]
    type = TimeDerivative
    variable = u
  []
  [u_diff]
    type = MatDiffusion
    variable = u
    diffusivity = D
  []
  [lam_dt]
    type = TimeDerivative
    variable = lam
  []
[]

[Materials]
  [D]
    type = GenericConstantMaterial
    prop_names = 'D'
    prop_values = '1e-3'
  []
[]

[Postprocessors]
  [ndofs]
    type = NumDOFs
    execute_on = 'timestep_end'
  []
  # 若 u 在低维块上有自由度，这个后处理器就能算出来
  [u_on_gbb]
    type = ElementIntegralVariablePostprocessor
    variable = u
    block = 2
    execute_on = 'timestep_end'
  []
  [u_on_gbb_max]
    type = NodalExtremeValue
    variable = u
    block = 2
    value_type = max
    execute_on = 'timestep_end'
  []
  [u_all]
    type = ElementIntegralVariablePostprocessor
    variable = u
    execute_on = 'timestep_end'
  []
  [u_bulk]
    type = ElementIntegralVariablePostprocessor
    variable = u
    block = '0 1'
    execute_on = 'timestep_end'
  []
[]

[Executioner]
  type = Transient
  dt = 1
  end_time = 1
  solve_type = NEWTON
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
