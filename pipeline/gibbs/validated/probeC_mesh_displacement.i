# =============================================================================
# 探针 C：网格位移能否带动**共形面块**（"正确 + 动态"路线的关键能力）
# =============================================================================
# 做法：y 方向加均匀应变 ε(t)=k·t（位移场 disp_y = ε·y）
#   ⇒ 面块是 x=const 的平面 ⇒ 其面积应随 (1+ε) 变化
#   ⇒ 纯拉伸无源 ⇒ ∫Γ dA 应守恒
# 判据：
#   C1  gb_area(t) / gb_area(0) == 1 + ε(t)      ⇒ 面块**跟着网格动**
#   C2  ∫Γ dA 守恒                               ⇒ 移动中面内守恒
#   正对照：ε=0 时面积不变
# =============================================================================
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 8
    ny = 8
    nz = 16
    xmin = 0
    xmax = 8e-9
    ymin = 0
    ymax = 8e-9
    zmin = 0
    zmax = 16e-9
  []
  [left]
    type = SubdomainBoundingBoxGenerator
    input = gen
    block_id = 1
    block_name = left
    bottom_left = '0 0 0'
    top_right = '4e-9 8e-9 16e-9'
  []
  [gb_ss]
    type = SideSetsBetweenSubdomainsGenerator
    input = left
    primary_block = 0
    paired_block = 1
    new_boundary = gb
  []
  [gb_block]
    type = LowerDBlockFromSidesetGenerator
    input = gb_ss
    sidesets = 'gb'
    new_block_id = 2
    new_block_name = gbb
  []
  displacements = 'disp_x disp_y disp_z'
[]

[Variables]
  [c]
    block = '0 1'
    initial_condition = 0.036
  []
  [Gam]
    block = 2
  []
[]

[ICs]
  [gam_ic]
    type = FunctionIC
    variable = Gam
    function = gam_init
  []
[]

[Functions]
  [zero_fn]
    type = ParsedFunction
    expression = '0'
  []
  [gam_init]
    type = ParsedFunction
    expression = '1e-6*(0.5+0.5*cos(2*pi*z/16e-9))'
  []
  # 均匀应变：ε(t) = 1e4 * t   （t_end=1e-6 ⇒ ε=1e-2）
  [strain_fn]
    type = ParsedFunction
    expression = '@EPSK@ * t * y'
  []
[]

[AuxVariables]
  [disp_x]
  []
  [disp_y]
  []
  [disp_z]
  []
[]

[AuxKernels]
  [disp_x_k]
    type = FunctionAux
    variable = disp_x
    function = zero_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
  [disp_y_k]
    type = FunctionAux
    variable = disp_y
    function = strain_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
  [disp_z_k]
    type = FunctionAux
    variable = disp_z
    function = zero_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  [c_dt]
    type = TimeDerivative
    variable = c
    block = '0 1'
  []
  [c_diff]
    type = MatDiffusion
    variable = c
    diffusivity = D_bulk
    block = '0 1'
  []
  [gam_dt]
    type = TimeDerivative
    variable = Gam
    block = 2
    use_displaced_mesh = true
  []
  [gam_surfdiff]
    type = MatDiffusion
    variable = Gam
    diffusivity = D_surf
    block = 2
    use_displaced_mesh = true
  []
[]

[Materials]
  [D_bulk]
    type = GenericConstantMaterial
    prop_names = 'D_bulk'
    prop_values = '4e-13'
  []
  [D_surf]
    type = GenericConstantMaterial
    prop_names = 'D_surf'
    prop_values = '4e-10'
  []
[]

[Postprocessors]
  [gb_area]
    type = AreaPostprocessor
    boundary = gb
    use_displaced_mesh = true
  []
  [gam_int]
    type = ElementIntegralVariablePostprocessor
    variable = Gam
    block = 2
    use_displaced_mesh = true
    execute_on = 'initial timestep_end'
  []
  [eps_meas]
    type = ParsedPostprocessor
    expression = '@EPSK@ * t'
    pp_names = ''
    use_t = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-20
  dt = 1e-7
  end_time = 1e-6
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-7
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]