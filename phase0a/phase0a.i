# =============================================================================
# Phase 0a：晶粒消失时溶质是否守恒？（平台可行性验证 + 核心实验）
# =============================================================================
#
# 目的：
#   在 MOOSE 中把"多晶粒长大（GrainTracker）"和"守恒的溶质浓度场"接起来，
#   测量每次晶粒消失时溶质总量的跳变。
#
# 背景（已从源码确认）：
#   - [Modules]/[PhaseField]/[GrainGrowth] 支持 c 参数
#   - 设了 c 之后，GrainGrowthAction 会为每个序参量自动加一个 ACGBPoly 核
#   - ACGBPoly 加的残差项是： L · 2·en_ratio · mu · gamma_asymm · eta_i · c²
#     （即晶界迁移驱动力与局部溶质浓度的耦合，也就是溶质拖曳）
#   - 材料需要提供 mu / gamma_asymm / L —— GBEvolution 全部提供，够用
#   - 重要限制：c 耦合不支持自动微分（AD 版 ACGBPoly 未实现），
#     所以 use_automatic_differentiation 必须是 false
#
# 要回答的三个问题：
#   1. 浓度场 c 在 GrainTracker 重映射（swapSolutionValues）之后还正确吗？
#   2. 每次晶粒消失，溶质总量跳变多少？
#   3. 跳变随步长减小是收敛的（数值问题）还是不收敛的（结构性问题）？
#
# 用法：
#   mpirun -np 8 ./phase_field-opt -i phase0a.i
#   python3 analyze.py .            # 出图（溶质漂移 vs 晶粒数）
#
# 变体实验（见文末）：把 ADAPTIVITY 打开再跑一遍，比较自适应网格的影响
# =============================================================================

# -----------------------------------------------------------------------------
# 网格：先用小网格快速跑通，确认没问题后再放大
# -----------------------------------------------------------------------------
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 40
  ny = 40
  xmax = 1000
  ymax = 1000
  elem_type = QUAD4
  uniform_refine = 1          # 80x80 有效网格，够快
[]

[GlobalParams]
  op_num = 8                  # 序参量个数（少于晶粒数，靠 GrainTracker 复用）
  var_name_base = gr
[]

# -----------------------------------------------------------------------------
# 晶粒长大：这里是关键 —— c = c 会启用 ACGBPoly
# -----------------------------------------------------------------------------
[Modules]
  [PhaseField]
    [GrainGrowth]
      c = c                                   # ← 启用溶质耦合（关键）
      en_ratio = 1.0                          # 表面能 / 晶界能 之比
      use_automatic_differentiation = false   # ← 必须 false，AD 版 ACGBPoly 未实现
    []
  []
[]

# -----------------------------------------------------------------------------
# 溶质浓度场（守恒量）。用最简的扩散方程，保证总量守恒。
# -----------------------------------------------------------------------------
[Variables]
  [c]
    order = FIRST
    family = LAGRANGE
    # 用随机初值，这样空间上有结构，能看出重映射有没有搞乱它
    [InitialCondition]
      type = RandomIC
      min = 0.2
      max = 0.5
    []
  []
[]

[Kernels]
  # ∂c/∂t = ∇·(D ∇c)
  # 周期边界下这个方程严格守恒 ∫c dV = const
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
  # 晶界参数：提供 L / kappa_op / mu / gamma_asymm，ACGBPoly 需要后两个
  # 参数取自官方示例（铜），先保证跑通，Ti64 参数后面再换
  [GB]
    type = GBEvolution
    T = 450
    wGB = 14
    GBmob0 = 2.5e-6
    Q = 0.23
    GBenergy = 0.708
  []

  # 溶质扩散系数（内部单位）。先取一个让扩散在仿真时间内可见的值。
  [solute_props]
    type = GenericConstantMaterial
    prop_names = 'D_c'
    prop_values = '1.0'
  []
[]

# -----------------------------------------------------------------------------
# 晶粒初始化
# -----------------------------------------------------------------------------
[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 30            # 初始 30 个晶粒，跑一段时间就会有消失事件
    rand_seed = 10
    int_width = 7
  []
  [grain_tracker]
    type = GrainTracker
    # 默认参数即可；如需调，关键的是 threshold 和 connecting_threshold
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
# 晶粒 ID 可视化（也用于统计晶粒数）
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

# -----------------------------------------------------------------------------
# 周期边界（保证溶质不外流，守恒性检验才有意义）
# -----------------------------------------------------------------------------
[BCs]
  [Periodic]
    [All]
      auto_direction = 'x y'
    []
  []
[]

# -----------------------------------------------------------------------------
# 后处理：这两个量就是整个实验的全部输出
# -----------------------------------------------------------------------------
[Postprocessors]
  # ① 溶质总量 —— 守恒性检验的核心指标
  [total_solute]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []

  # ② 晶粒数 —— 用于识别晶粒消失事件
  #    对 unique_grains（晶粒 ID）做连通域计数：
  #    unique_grains 在晶粒内部 > 0，在晶界处为 0 或负，
  #    所以用"大于阈值"找连通域 = 找晶粒
  [ngrains]
    type = FeatureFloodCount
    variable = unique_grains
    threshold = 0.5
    use_less_than_threshold_comparison = false
    execute_on = 'initial timestep_end'
  []

  # ③ 晶界总面积 —— 辅助判据（晶粒消失时应该下降）
  #    注意：GrainBoundaryArea 用的是 v（序参量数组），不是 variable。
  #    它的 v 参数是 addRequiredCoupledVarWithAutoBuild，会从 GlobalParams 的
  #    var_name_base / op_num 自动构建，所以这里不用手写变量列表。
  [gb_area]
    type = GrainBoundaryArea
    execute_on = 'initial timestep_end'
  []

  # ④ 时间步长 —— 用于"跳变是否随步长收敛"的对比
  [dt]
    type = TimestepSize
  []

  # ⑤⑥ 浓度场的极值 —— 用于确认 c 真的在扩散（而不是被冻住）
  #     随机初值扩散后，max 会降、min 会升；若两者都不变，说明场的演化是假的
  #     注意：MOOSE 里没有 NodalMinValue，极值统一用 NodalExtremeValue + value_type
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
[]

# -----------------------------------------------------------------------------
# 求解器
# -----------------------------------------------------------------------------
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

  end_time = 1500

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 20
    optimal_iterations = 6
  []

  # ---- 变体实验：把下面这段注释掉/打开，比较自适应网格的影响 ----
  # 自适应网格会改变离散化（加/删单元），是"离散化变化"的一个来源。
  # 先关掉，隔离出 GrainTracker 重映射的单独影响。
  # [Adaptivity]
  #   initial_adaptivity = 2
  #   refine_fraction = 0.8
  #   coarsen_fraction = 0.05
  #   max_h_level = 2
  # []
[]

[Outputs]
  csv = true
  exodus = true
  execute_on = 'initial timestep_end'
  print_linear_residuals = false
[]
