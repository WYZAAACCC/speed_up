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
#   域 430 × 150 um，dx = 1 um -> 64500 单元
#
# -----------------------------------------------------------------------------
# 【本文件 = Ti64 真实参数版】（2026-09-17）
#
# 相对 stage1_meltpool.i（铜参数版）只改了三组数：
#   sigma   : 0.708 -> 0.6    J/m^2   (Ti64 β/β 晶界能)
#   GBmob0  : 2.5e-6 -> 232   m^4/(J*s)
#   Q       : 0.23  -> 3.234  eV
# 派生量随之变为 mu0 = 9.0e5，kappa_op = 1.8e-6。
#
# ⚠️ **M0 与 Q 必须成对替换**，只换一个一定错 —— 理由与出处见
#    [Materials]/L_mobility 的注释（那里有完整推导与校验）。
#
# ⚠️ 文献对 Q 有 3 倍分歧，本版取高 Q 组；定量前需做敏感性分析。
# -----------------------------------------------------------------------------
# 【v1 -> v2 改动】（v1 备份见 stage1_meltpool_v1_backup.i）
#
#   v1 跑通后测出的问题：**固态粗化压过了凝固**。
#   末态晶粒 y 跨度涨到整个域深 69 um，而熔池从未到过的左侧区域
#   也发生了明显粗化 —— 说明长大不是凝固驱动的。
#
#   根因与修法：
#   1. **L 原来是常数**，353 K 冷区与 1900 K 热区同样速率粗化。
#      -> 改成 Arrhenius 温度相关（见 [Materials]/L_mobility）。
#      这是本轮最关键的修正。
#   2. **域太浅（70 um）**，熔池深 40 um，留给基体只有 30 um，
#      晶粒 y 跨度被卡死，物理上不可能显示柱状伸长。
#      -> 加深到 150 um，熔池占 27%，接近 LPBF 实际（池浅、基体厚）。
#   3. grain_num 20 -> 36，保持晶粒尺寸 ~40 um 不变。
#
# 【仍待处理】
#   - 不含溶质场 c（stage1_meltpool_c.i 已就绪）
#   - **GBmob0 / Q / GBenergy 仍是铜的值**，待换 Ti64（方案 §0b）
#   - 基体是等轴 Voronoi，真实 LPBF 基体是上一层的柱状晶
#   - 熔池深处可能因数值噪声自发形核（非物理）—— 看它多严重
# =============================================================================

[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 430
    ny = 150
    xmin = -2.8e-4
    xmax =  1.5e-4
    ymin =  0.0
    ymax =  1.5e-4
    # 【2026-09-17 改】原为 70 um 深。熔池深 ~40 um，留给基体只有 30 um，
    # 晶粒 y 跨度被域深卡死，物理上不可能显示柱状伸长。
    # 加深到 150 um 后熔池占 27%，接近 LPBF 实际情况（池浅、基体厚）。
    # 代价：单元数 30100 -> 64500。
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
    grain_num = 36          # 域加深后相应增加，保持晶粒 ~40 um
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
      # L 现在依赖 T -> ACInterface 需要变量的导数，故必须 variable_mobility = true
      # 并把 T 作为 coupled_variables 传进去
      variable_mobility = true
      coupled_variables = 'T'
      mobility = L
      kappa = kappa_op
    []
  []
[]

[Materials]
  # 【2026-09-17 换成 Ti64 β 相真实值】
  #   sigma = 0.6 J/m^2
  #     出处 Gornakova & Prokofjev, J. Mater. Sci. 55 (2020) 9225, Eq.(6)
  #     β/β 大角晶界，1000-1300 C 区间 0.68->0.57，取中间代表值 0.6
  #     交叉验证：同文的纯 β-Ti 值 gamma = 453-0.36(T-Tm) mJ/m^2，
  #     与 Ti64 差 <2% —— 说明 Al/V 合金化对 β/β 晶界能影响很小；
  #     另有独立 MD (He, Ma & Wang, Materials 15 (2022) 156) 给出
  #     多晶平均 0.6-0.7 J/m^2，一致。
  #
  #   mu0   = 6 * sigma / wGB = 6 * 0.6 / 4e-6 = 9.0e5
  #   kappa = 0.75 * sigma * wGB = 0.75 * 0.6 * 4e-6 = 1.8e-6
  #   gamma = 1.5（与 GBEvolution 一致）
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'kappa_op  gamma_asymm'
    prop_values = '1.8e-6    1.5'
  []

  # 【2026-09-17 关键修正】晶界迁移率 L 改为温度相关（Arrhenius）
  #
  #   原来 L 是常数 0.2013，意味着 353 K 的冷区与 1900 K 的热区
  #   以**完全相同的速率**粗化。结果激光走后整个域持续全速长大，
  #   固态粗化压过了凝固 —— 实测末态晶粒 y 跨度涨到整个域深 69 um，
  #   而熔池从未到过的左侧区域也发生了明显粗化。
  #
  #   M_GB = GBmob0 * exp(-Q/(kb*T))      （GBEvolutionBase 的原始形式）
  #   L    = 4/3 * M_GB / wGB
  #   kb   = 8.617e-5 eV/K
  #
  #   在 T=1878 K 时 L = 0.2013，与原常数一致；T=353 K 时 L 小约 465 倍，
  #   冷区长大被有效冻结。
  #
  # ⚠️ 下面这组是 **Ti64 β 相的真实值**（不再是铜的）。
  #
  #   GBmob0 = 232 m^4/(J*s)，Q = 3.234 eV (= 312 kJ/mol)
  #     出处 Pilchak, Sargent & Semiatin, Metall. Mater. Trans. A 49 (2018)
  #     908-919, Eq.[5]（开放获取）。原始拟合 M = 139*exp(-37525/T)，
  #     建立在 gamma = 1 J/m^2 的假定上；文献实际拟合的是乘积 8*M*gamma，
  #     所以换用 gamma = 0.6 后必须把 M0 放大到 139/0.6 ≈ 232，
  #     否则晶粒长大速率会慢 40%。校验：232*0.6 = 139 ✓
  #
  #     该值经实验校验：按此式预测 1088 C 保温 50 s 晶粒 50->247 um，
  #     实测 230 um，吻合 7% 以内。
  #
  #   【重要】M0 与 Q **必须成对替换**。
  #     铜: M0=2.5e-6, Q=0.23 eV -> 450 K 时 M=6.6e-9
  #     Ti64: M0=232, Q=3.234 eV -> 1300 C 时 M=6.0e-9
  #     两者在高温度下几乎相等（Ti64 的 M0 大 5 个数量级，但 Q 高 14 倍，
  #     被指数项压回来）。只换 M0 不动 Q 一定错。
  #
  #   【物理后果】Q 大 -> 迁移率随温度掉得极快：
  #     1878 K: M ~ 4.9e-7   (L ~ 0.16)
  #     1500 K: M ~ 3.2e-9   (掉了 150 倍)
  #     1200 K: M ~ 5.8e-12  (掉了 8e4 倍)
  #     1000 K: M ~ 1.1e-14
  #     353 K : M ~ 1e-46    (完全冻结)
  #   即：冷区长大被彻底冻结，组织完全由凝固决定。这正是我们要的。
  #
  #   【已知风险】文献对 Q 有 3 倍分歧：
  #     低 Q 家族 91-98 kJ/mol (0.94-1.02 eV)，Gil & Planell 1991
  #     高 Q 家族 227/251/312 kJ/mol，Ivasishin 2002 / Semiatin 1994 / 1996
  #   这里取高 Q 组，因为它通过了 1088 C 实测数据校验。
  #   定量结论前必须做敏感性分析（用低 Q 组再跑一次）。
  [L_mobility]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T'
    constant_names = 'GBmob0 Q kb wGB'
    constant_expressions = '232 3.234 8.617e-5 4.0e-6'
    expression = '4.0/3.0 * GBmob0 * exp(-Q/(kb*T)) / wGB'
    derivative_order = 1
  []

  # 温度相关的势垒 mu —— 熔池内变负
  [barrier_mu]
    type = DerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
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
    # 【每一步都存】面拓扑每步都在变，隔步存会漏掉大部分拓扑事件，
    # 而转移算子正是靠这些事件训练的。文件大不是问题（存在 F 盘）。
    time_step_interval = 1
    file_base = stage1
  []
[]
