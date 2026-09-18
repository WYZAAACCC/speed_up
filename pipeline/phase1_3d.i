# =============================================================================
# 阶段 1：3D 数据生成算例
# =============================================================================
#
# 目的：让 MOOSE 产出构建"晶粒图 + 逐面溶质"所需的全部量：
#   unique_grains —— 元素级晶粒 ID（晶粒图的唯一来源）
#   c            —— 溶质浓度场
#   bnds         —— 晶界指示函数
#   gr0..grN     —— 序参量
#
# 已验证（阶段 1.0）：上面这些在 2D 算例的 Exodus 里全都写出来了。
# 本文件把它们搬到 3D，并调整规模使其能在这台机器上跑。
#
# 【规模选择的现实约束】
#   3D 里要解析晶界，单元尺寸必须 ≲ wGB/3。
#   若域 1000、20 晶粒、wGB=10 → 晶粒 ~74、需 ~370³ ≈ 5000 万单元，笔记本跑不动。
#   所以这里把域缩小、wGB 相对放大：
#     域 200³、20 晶粒、wGB=10、单元尺寸 3.33 → 60³ = 216,000 单元
#   wGB/晶粒 ≈ 13%（与 MOOSE 官方 2D 示例的 14% 同量级，可接受）
#
# 用法：
#   mpirun -np 12 phase_field-opt -i phase1_3d.i
#
# 计时参考：先跑通看墙钟时间，再决定是否放大
# =============================================================================

[Mesh]
  # 【规模是实测定的，不是拍的】
  #   第一版用 60³ = 216,000 单元 × 21 变量，跑十几分钟完不成一个时间步，
  #   把 Windows 内存吃到只剩 2.5 GB，整个系统换页卡死。
  #   这里降到 40³ = 64,000 单元（小 3.4 倍），并把晶界相对放大以保持可解析。
  type = GeneratedMesh
  dim = 3
  nx = 20
  ny = 20
  nz = 20
  xmax = 200
  ymax = 200
  zmax = 200
  elem_type = HEX8
  uniform_refine = 1          # → 40×40×40 = 64,000 单元
  #   单元尺寸 = 5；wGB = 15 → 晶界上跨 3 个单元（可解析）
  #   晶粒尺寸 = 200 / 30^(1/3) ≈ 64；wGB/晶粒 ≈ 23%（偏厚，但拓扑与输运研究可接受）
[]

[GlobalParams]
  # 【为什么是 20】
  #   3D 里每个晶粒平均有 ~14 个邻居，序参量数必须够多，才能保证
  #   "相邻的晶粒不会共用同一个序参量"（否则它们一接触就会被非物理地合并）。
  #   MOOSE 报错信息给的量级："~8 for 2D, ~25 for 3D"。
  #   50 晶粒配 20 序参量，比官方 3D 示例（100 晶粒 / 18 序参量）更宽松。
  op_num = 20
  var_name_base = gr
[]

# -----------------------------------------------------------------------------
# 晶粒长大 + 溶质耦合（c = c 启用 ACGBPoly）
# -----------------------------------------------------------------------------
[Modules]
  [PhaseField]
    [GrainGrowth]
      c = c
      en_ratio = 1.0
      use_automatic_differentiation = false   # 必须 false，AD 版 ACGBPoly 未实现
    []
  []
[]

# -----------------------------------------------------------------------------
# 溶质浓度场（守恒量）
# -----------------------------------------------------------------------------
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
    wGB = 15                  # 与网格匹配：单元尺寸 5 → 晶界上跨 3 个单元
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

# -----------------------------------------------------------------------------
# 晶粒初始化（Voronoi 天然支持 3D）
# -----------------------------------------------------------------------------
[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 30            # 30 个晶粒，目标是粗化掉 5–10 个
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

# -----------------------------------------------------------------------------
# 元素级晶粒 ID —— 晶粒图的唯一来源
# -----------------------------------------------------------------------------
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
      auto_direction = 'x y z'
    []
  []
[]

# -----------------------------------------------------------------------------
# 后处理
# -----------------------------------------------------------------------------
[Postprocessors]
  # 总溶质量 —— 全局守恒性检查
  [total_solute]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []
  # 晶粒数（GrainTracker 直接给出）
  [ngrains]
    type = FeatureFloodCount
    variable = unique_grains
    threshold = 0.5
    use_less_than_threshold_comparison = false
    execute_on = 'initial timestep_end'
  []
  # 浓度场极值 —— 确认场在演化
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

  end_time = 3000

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 20
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  # 每步都写 Exodus 太占空间，按间隔写（CSV 每步都记）
  [exodus_out]
    type = Exodus
    time_step_interval = 5        # 参数名是 time_step_interval（基类 Output），不是 interval
    file_base = phase1_3d
    execute_on = 'initial timestep_end'
  []
[]
