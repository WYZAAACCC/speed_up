# =============================================================================
# 阶段一：LPBF 单熔池凝固
# =============================================================================
#
# 【物理图景】（2026-09-17 按用户纠正调整）
#   温度场是**已熔融液态金属**的温度场。我们**不从冷固体开始用激光去熔**，
#   而是直接从一个已经形成的熔池出发，看它如何凝固。
#
#   t=0 的初值：熔池内 = 液态（η=0），熔池外 = 固态多晶（Voronoi）
#   随激光右移，熔池尾部冷却 -> 从基体外延长出柱状晶
#
# 【要验证什么】
#   1. 熔池能保持液态（不自行结晶）
#   2. 尾部能外延生长出柱状晶
#   3. GrainTracker 的序参量槽位会不会耗尽   <- 真正的风险
#
# 【核心机制】—— 不编译 C++，全部用现成对象
#
#   Allen-Cahn 方程（GrainGrowthAction 生成的核）：
#       dη/dt = -L·mu·(η³ - η + 2γ·η·Ση_j²) - L·kappa_op·∇²η
#                └──────── 体驱动力 ────────┘   └── 界面项 ──┘
#
#   ACGrGrPoly 的驱动力正比于材料属性 `mu`（属性名硬编码，见 ACGrGrBase）。
#   让 mu 在液相线以上变负 -> 有序态不再是极小值 -> η 被压到 0（液态），
#   且液态成为稳定态（不会自发结晶）。降到液相线以下 mu 转正 -> 凝固开始。
#   kappa_op 始终为正，界面项不受影响。
#
#   mu(T) = mu0 · [1 - (1+boost)·½(1+tanh((T-T_mid)/dT))]
#       T << T_mid  -> mu = +mu0        （固态，正常长大）
#       T >> T_mid  -> mu = -boost·mu0  （液态，稳定）
#
# 【单位】全程 SI：长度 m，时间 s，温度 K
#
# 【几何】2D 纵截面（x = 扫描方向，y = 深度）
#   熔池（P=80W, v=0.6m/s）：宽 60 um，深 30 um，尾长 137 um
#   域 430 × 70 um，dx = 1 um -> 30100 单元
#
# 【第一版故意留着的粗糙处】
#   - 不含溶质场 c（下一步加）
#   - L 是常数（未用 Arrhenius 温度依赖）
#   - 熔池深处可能因数值噪声自发形核（非物理）—— 看它多严重
# =============================================================================

[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 430
    ny = 70
    xmin = -2.8e-4
    xmax =  1.5e-4
    ymin =  0.0
    ymax =  7.0e-5
    elem_type = QUAD4
  []
  # 用 t=0 时刻的 Rosenthal 等温线精确划出初始熔池（激光在 x=-1.2e-4）
  # 判据：温度超出量 > (T_liquidus - T_room) = 1928 - 300 = 1628 K
  # 表达式即 Rosenthal 解，t=0 -> xi = x + 1.2e-4
  #
  # 【坑】这里的解析器**不认识 pi**（ParsedFunction 里可用，网格生成器里不行，
  # 报 "Syntax error: Unknown identifier"）。所以把常数折叠成数值：
  #   eta*P/(2*pi*k) = 28/(2*pi*20) = 0.222817
  #   v/(2*alpha)    = 0.6/(2*6e-6) = 50000
  [liquid_pool]
    type = ParsedSubdomainMeshGenerator
    input = gen
    combinatorial_geometry = '0.222817/sqrt((x+1.2e-4)^2+y^2+1e-10)*exp(-50000*(sqrt((x+1.2e-4)^2+y^2+1e-10)+x+1.2e-4)) > 1628'
    block_id = 1
    block_name = liquid
  []
[]

[GlobalParams]
  op_num = 8
  var_name_base = gr
[]

[Functions]
  # 移动高斯热源（Rosenthal 解），SI 单位
  #   P=80 W, eta=0.35 -> 吸收 28 W
  #   v=0.6 m/s, k=20 W/(m*K), alpha=6e-6 m^2/s
  # 【踩过的两个坑】
  #   1. symbol_values 只能是「数字」或「对象名」，不能是表达式
  #      （写成表达式要到运行时才报错，--check-input 查不出来）
  #   2. symbol_values 按空白切分，内部不能有空格
  # 所以整条表达式内联，并用 +1e-10 避免 R=0 除零。
  [laser_T]
    type = ParsedFunction
    expression = '353 + 28/(2*pi*20*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-0.6*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+x+1.2e-4-0.6*t)/(2*6e-06))'
  []
[]

[Variables]
  [PolycrystalVariables]
  []
[]

[ICs]
  # Voronoi 多晶，**只加在固态区（block 0）**；
  # 液态区（block 1）保持变量默认初值 0
  [PolycrystalICs]
    [PolycrystalColoringIC]
      polycrystal_ic_uo = voronoi
      block = 0
    []
  []
[]

[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 20
    rand_seed = 2024
    int_width = 4.0e-6      # 界面宽 4 um = 4 个单元
  []
  [grain_tracker]
    type = GrainTracker
  []
[]

[AuxVariables]
  [T]
    initial_condition = 353
  []
  [unique_grains]
    order = CONSTANT
    family = MONOMIAL
  []
  [liquid_flag]
    order = CONSTANT
    family = MONOMIAL
  []
  # 不需要声明 bnds —— GrainGrowthAction 会自动创建
[]

[AuxKernels]
  [T_field]
    type = FunctionAux
    variable = T
    function = laser_T
    execute_on = 'initial timestep_end'
  []
  [unique_grains]
    type = FeatureFloodCountAux
    variable = unique_grains
    flood_counter = grain_tracker
    field_display = UNIQUE_REGION
    execute_on = 'initial timestep_end'
  []
  [liquid_flag]
    type = ParsedAux
    variable = liquid_flag
    coupled_variables = 'T'
    expression = 'if(T>1903,1,0)'
    execute_on = 'initial timestep_end'
  []
[]

[Modules]
  [PhaseField]
    [GrainGrowth]
      variable_mobility = false      # L 是常数 -> ACInterface 的 variable_L = false
      mobility = L
      kappa = kappa_op
    []
  []
[]

[Materials]
  #   mu0   = 3/4 * 1/f0s * sigma / wGB = 6 * 0.708 / 4e-6
  #   kappa = 3/4 * sigma * wGB         = 0.75 * 0.708 * 4e-6
  #   L     = 4/3 * M_GB / wGB,  M_GB(T=1878K) = 2.5e-6*exp(-0.23/(kb*1878))
  #   gamma = 1.5（与 GBEvolution 一致）
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'L      kappa_op  gamma_asymm'
    prop_values = '0.2013 2.124e-6  1.5'
  []

  # 温度相关的势垒 mu —— 熔池内变负
  [barrier_mu]
    type = DerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '1.062e6 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
  []
[]

[Postprocessors]
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [liquid_frac]
    type = ElementAverageValue
    variable = liquid_flag
    execute_on = 'initial timestep_end'
  []
  [mu_avg]
    type = ElementAverageMaterialProperty
    mat_prop = mu
    execute_on = 'initial timestep_end'
  []
  [dt]
    type = TimestepSize
  []
[]

[Preconditioning]
  # 【必须是 SMP full】—— PJFNK + hypre boomeramg 会线性发散（phase2_prod.i 已踩过）
  [coupled]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON

  # 这套配置来自 phase2_prod.i（已验证可用）
  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -sub_pc_asm_overlap'
  petsc_options_value = 'asm      31                  preonly       ilu          1'

  l_max_its = 30
  l_tol = 1e-6
  nl_max_its = 50
  nl_rel_tol = 1e-8
  # 1e-9 太紧：实测残差停在 8.5e-8，线性求解打不到更低就报 DIVERGED_ITS
  nl_abs_tol = 1e-7

  # 激光从 x=-1.2e-4 扫到域外；再留时间让尾部凝固
  end_time = 6.5e-4

  # 【关键】必须限制最大步长（是 Executioner 的 dtmax，不是 TimeStepper 的参数）。
  # 界面弛豫时间 1/(L*mu) = 1/(0.2*1.06e6) ~ 4.7e-6 s。
  # 不限制时自适应步长按 1.5x 一路涨，实测到 dt~7.6e-6 时
  # 线性求解就 DIVERGED_ITS（残差先停滞再发散）。
  dtmax = 2e-6

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-6
    cutback_factor = 0.5
    growth_factor = 1.5
    optimal_iterations = 5
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  [exo]
    type = Exodus
    time_step_interval = 5
    file_base = stage1
  []
[]
