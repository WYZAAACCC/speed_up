# =============================================================================
# 阶段 2（含晶界偏析版）—— 2D 主线生产算例
# =============================================================================
#
# 【为什么需要这个版本】
#   前一版把 c 当成"纯扩散场"：∂c/∂t = ∇·(D∇c)，它会把浓度推向均匀，
#   晶界上不会富集。而我们的整个物理故事建立在"晶界上有偏析的溶质"之上。
#
# 【怎么修】
#   MOOSE 的 ACGBPoly 给 η 方程加了一项，对应自由能里的  A·(Ση_i²)·c²。
#   但 c 方程里没有对应项，所以偏析建立不起来。
#   这里把 c 改用 Cahn-Hilliard 形式（化学势驱动），并把同一项写进自由能：
#
#       f(c, η) = k/2·(c - c0)²  +  A·c²·(Ση_i²)
#
#   化学势  μ = ∂f/∂c = k·(c-c0) + 2A·c·(Ση_i²)
#
#   体相 Ση²=1，晶界 Ση²≈0.5，两者化学势相等给出
#       c_gb / c_b = (k + 2A)/(k + A)  > 1     ← 晶界富集
#
#   这样 η 方程（ACGBPoly）和 c 方程（SplitCHParsed）来自同一个自由能，
#   变分自洽。
#
# 【与上一版的差别】
#   + 新增化学势变量 w
#   + c 的三个核换成 split Cahn-Hilliard
#   + 新增自由能材料 f_loc、迁移率 M、梯度系数 kappa_c
#   其余（网格、晶粒、GrainTracker、输出）不变
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 50
  ny = 50
  xmax = 1000
  ymax = 1000
  elem_type = QUAD4
  uniform_refine = 2          # → 200×200 = 40,000 单元，单元尺寸 5
[]

[GlobalParams]
  op_num = 10
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
  # 浓度场
  # 【初始条件改成均匀】原来是 [0.30,0.40] 的随机场，梯度大，
  # 叠加偏析驱动力后瞬态过冲，c 越界到 [−0.5, 1.04]。
  # 改成均匀初值，让偏析自己慢慢建立。
  [c]
    order = FIRST
    family = LAGRANGE
    [InitialCondition]
      type = RandomIC
      min = 0.3499
      max = 0.3501
    []
  []
  # 化学势（split CH 引入的辅助变量）
  [w]
    order = FIRST
    family = LAGRANGE
  []
[]

[Kernels]
  # ---- split Cahn-Hilliard：∂c/∂t = ∇·(M ∇μ) ----
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
  []
[]

[Materials]
  # ---- 晶界参数（提供 mu / gamma_asymm / L，ACGBPoly 需要）----
  [GB]
    type = GBEvolution
    T = 450
    wGB = 14
    GBmob0 = 2.5e-6
    Q = 0.23
    GBenergy = 0.708
  []

  # ---- 自由能 f_loc = k/2(c-c0)^2 + A·c²·(Ση_i²) ----
  #
  # 【必须与 ACGBPoly 的形式一致！—— 踩过的坑】
  #   一度把这里改成线性项 A·c·Ση²，想让富集更强。
  #   但 ACGBPoly 是编译好的核，实现的仍是二次耦合：
  #       dF/dη_i = 2·en_ratio·mu·gamma·η_i·c²   →   F 含 en_ratio·mu·gamma·(Ση²)·c²
  #   两边形式不一致 → 变分不自洽 → 序参量幅值衰减
  #   （实测 Ση² 的体相最大值从 1.0 掉到 0.73）。
  #   所以这里必须写回二次形式，与 ACGBPoly 对齐。
  #
  # 【平衡时的偏析】
  #   μ = ∂f/∂c = k(c-c0) + 2A·c·Ση²
  #   体相 Ση²=1，晶界 Ση²≈0.5，两者 μ 相等：
  #       c_GB / c_bulk = (k + 2A)/(k + A)  > 1     ← 晶界富集
  #
  # 【求解器已修好】
  #   之前发散是 PJFNK + hypre boomeramg 不适合 c-w 耦合系统，
  #   换成 NEWTON + SMP full=true + asm/ilu 后已稳定（见下方 Preconditioning）。
  [local_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7 gr8 gr9'
    material_property_names = 'mu gamma_asymm'
    # A_scale 控制偏析强度，平衡富集比 = (k+2A)/(k+A)，上限 2×
    constant_names = 'k c0 en_ratio A_scale'
    constant_expressions = '1.0 0.35 1.0 0.5'
    expression = 'k/2*(c-c0)^2
                  + A_scale*en_ratio*mu*gamma_asymm*c^2
                    *(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2
                     +gr5^2+gr6^2+gr7^2+gr8^2+gr9^2)'
  []

  # ---- 迁移率与梯度系数 ----
  #   D = M*k = 1 是体扩散系数
  #   kappa_c 取小值：c 的剖面宽度由 Ση² 的剖面决定（~晶界宽度 14，可解析），
  #   不需要靠 κ 撑出细界面
  [ch_params]
    type = GenericConstantMaterial
    prop_names = 'M kappa_c'
    prop_values = '1.0 1.0'
  []
[]

[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    # 【多分散种子】不用随机的等尺寸结构，改用外部种子文件。
    # 里面故意塞了 15 个偏小的晶粒（等效直径 ~30，约 2× 晶界宽度），
    # 它们会在最初几百个时间单位内消失，从而在低成本区间内产生拓扑事件。
    # 等尺寸结构要粗化上千时间单位才掉晶粒，而含偏析的 CH 系统很贵，等不起。
    # 注意：给了 file_name 后 grain_num 会被忽略（MOOSE 会警告）。
    file_name = seeds_poly.txt
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
  # 晶界指示（用于诊断偏析）
  [gb_indicator]
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
  # Ση_i²：体相 ≈1，晶界 ≈0.5
  [gb_indicator]
    type = ParsedAux
    variable = gb_indicator
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7 gr8 gr9'
    expression = 'gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2+gr8^2+gr9^2'
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
  # 注意：晶界区 vs 体相的浓度对比在 Python 里从 Exodus 算
  #       （c 和 gb_indicator 都会写进 Exodus，做条件平均即可）
  [dt]
    type = TimestepSize
  []
[]

# 【求解设置 —— 按 MOOSE 官方 Cahn-Hilliard 示例改】
#   原来用 PJFNK + hypre boomeramg 会线性发散（DIVERGED_ITS 50 次迭代）。
#   boomeramg 是为标量扩散设计的，处理不了 c-w 耦合系统。
#   官方 s1/s3 示例的做法是：SMP full=true 组装完整耦合雅可比 + NEWTON + asm/ilu。
[Preconditioning]
  [coupled]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON

  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'
  petsc_options_value = 'asm      31                  preonly       ilu          1'

  l_max_its = 30
  l_tol = 1e-6
  nl_max_its = 50
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-9

  end_time = 4000

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 10
    cutback_factor = 0.8
    growth_factor = 1.5
    optimal_iterations = 7
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  [exodus_out]
    type = Exodus
    time_step_interval = 1
    file_base = phase2_2d_seg
    execute_on = 'initial timestep_end'
  []
[]
