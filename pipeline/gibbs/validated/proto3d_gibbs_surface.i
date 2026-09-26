# =============================================================================
# 3D Gibbs 面最小原型：在 3D 体网格里造一个 **2D 面块**，把 Γ 挂上去
# =============================================================================
# 关键问题（生死线 ①）：Γ 能不能是一个**真正的面上自由度**？
#   · 面 = 3D 网格的内侧面 → LowerDBlockFromSidesetGenerator 做成低维块（2D 元）
#   · Γ 定义在那个块上 ⇒ 面天生共形，**不用 remesh、不用 MultiApp**
# 判据：
#   A1 面块的面测度正确：Area(block=2) 应 = Ly*Lz = 8e-9 * 16e-9 = 1.28e-16 m^2
#   A2 Γ 能承载一个**面内扩散**方程（沿 z 的余弦应衰减，∫Γ dA 守恒）
#   A3 Γ 不在体相里存在（体相块 0/1 上无 Gam 自由度）
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
[]

[Variables]
  # 体相浓度（两个晶粒块）
  [c]
    block = '0 1'
    initial_condition = 0.036
  []
  # ★ 面上的 Gibbs 过剩 Γ（只在低维块 2 上有自由度）
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
  # 沿 z 的零均值余弦 ⇒ 应沿面扩散而衰减
  [gam_init]
    type = ParsedFunction
    expression = '1e-6*(0.5+0.5*cos(2*pi*z/16e-9))'
  []
[]

[Kernels]
  # --- 体相：普通扩散（让体相块有方程，否则块 0/1 上无变量）---
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
  # --- ★ 面：Γ 的时间演化 + **面内扩散** ---
  [gam_dt]
    type = TimeDerivative
    variable = Gam
    block = 2
  []
  [gam_surfdiff]
    type = MatDiffusion
    variable = Gam
    diffusivity = D_surf
    block = 2
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
  # A1：面块的面测度（应 = 8e-9*16e-9 = 1.28e-16）
  [gb_area]
    type = AreaPostprocessor
    boundary = gb
  []
  # A2：∫Γ dA 应守恒；max/min 应衰减
  [gam_int]
    type = ElementIntegralVariablePostprocessor
    variable = Gam
    block = 2
    execute_on = 'initial timestep_end'
  []
  [gam_max]
    type = NodalExtremeValue
    variable = Gam
    value_type = max
    block = 2
    execute_on = 'timestep_end'
  []
  [gam_min]
    type = NodalExtremeValue
    variable = Gam
    value_type = min
    block = 2
    execute_on = 'timestep_end'
  []
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    block = '0 1'
    execute_on = 'timestep_end'
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
  dt = 5e-9
  end_time = 1e-6
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 5e-9
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]