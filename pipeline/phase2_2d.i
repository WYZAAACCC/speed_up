# =============================================================================
# 阶段 2：2D 主线的生产算例（事件密集版）
# =============================================================================
#
# 目的：产出足够多的"晶粒消失"事件，用于
#   (a) 量化现有方法在拓扑事件处处理溶质转移的偏差        ← 问题篇
#   (b) 训练逐面学习算子                                  ← 解法篇
#
# 与 phase0a.i 的区别：
#   - 网格 80² → 200²（更细，界面更清晰）
#   - 晶粒 30 → 60（更多事件）
#   - 时间 1500 → 4000（充分粗化）
#   - 输出加了逐时刻的完整场（Exodus 每步都写，因为要追踪每个面的演化）
#
# 规模论证：
#   域 1000，nx=50 + uniform_refine=2 → 单元尺寸 5
#   wGB = 14 → 晶界上跨 2.8 个单元（与 MOOSE 官方示例的 2.5 同量级）
#   2D 下 40,000 单元 × 12 变量，成本远低于 3D，可以跑长
#
# 用法：
#   mpirun -np 8 phase_field-opt -i phase2_2d.i
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 50
  ny = 50
  xmax = 1000
  ymax = 1000
  elem_type = QUAD4
  uniform_refine = 2          # → 200×200 = 40,000 单元
[]

[GlobalParams]
  op_num = 10                 # 2D 邻接度低，10 个够（官方示例 100 晶粒用 8 个）
  var_name_base = gr
[]

[Modules]
  [PhaseField]
    [GrainGrowth]
      c = c
      en_ratio = 1.0
      use_automatic_differentiation = false
    []
  []
[]

[Variables]
  [c]
    order = FIRST
    family = LAGRANGE
    [InitialCondition]
      type = RandomIC
      min = 0.2
      max = 0.5
    []
  []
[]

[Kernels]
  [c_time]
    type = TimeDerivative
    variable = c
  []
  [c_diffusion]
    type = MatDiffusion
    variable = c
    diffusivity = D_c
  []
[]

[Materials]
  [GB]
    type = GBEvolution
    T = 450
    wGB = 14
    GBmob0 = 2.5e-6
    Q = 0.23
    GBenergy = 0.708
  []
  [solute_props]
    type = GenericConstantMaterial
    prop_names = 'D_c'
    prop_values = '1.0'
  []
[]

[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 60
    rand_seed = 10
    int_width = 7
  []
  [grain_tracker]
    type = GrainTracker
  []
[]

[ICs]
  [PolycrystalICs]
    [PolycrystalColoringIC]
      polycrystal_ic_uo = voronoi
    []
  []
[]

[AuxVariables]
  [unique_grains]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [unique_grains]
    type = FeatureFloodCountAux
    variable = unique_grains
    flood_counter = grain_tracker
    field_display = UNIQUE_REGION
    execute_on = 'initial timestep_end'
  []
[]

[BCs]
  [Periodic]
    [All]
      auto_direction = 'x y'
    []
  []
[]

[Postprocessors]
  [total_solute]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [dt]
    type = TimestepSize
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = PJFNK

  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'

  l_max_its = 50
  l_tol = 1e-4
  nl_max_its = 15
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-10

  end_time = 4000

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 20
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  # 每个时间步都写 Exodus —— 追踪面的演化需要连续的时间序列
  [exodus_out]
    type = Exodus
    time_step_interval = 1
    file_base = phase2_2d
    execute_on = 'initial timestep_end'
  []
[]
