# =============================================================================
# 阶段一（含溶质）：LPBF 单熔池凝固 + 溶质场
# =============================================================================
#
# 在 stage1_meltpool.i 的基础上加溶质场 c。其余部分完全相同。
#
# 【为什么要加溶质】
#   逐面神经算子学的是**溶质再分配**，所以参考解必须带溶质场，
#   且 extract.py 需要 `c` 和 `unique_grains`。
#
# 【溶质怎么分凝】—— 复用 MOOSE 的 Cahn-Hilliard 分裂形式
#
#   自由能：f_loc = k_c/2·(c-c0)² + A_part·c²·Ση_i²
#                                     └──── 液相/固相区分项 ────┘
#
#   本模型里 液相 = 所有 η = 0（Ση²=0），固相 = 某个 η = 1（Ση²=1）。
#   所以第二项**只在固相起作用**，把溶质从固相里挤出去：
#
#       液相 (Ση²=0):  ∂f/∂c = k_c(c-c0) = 0        -> c_L = c0
#       固相 (Ση²=1):  k_c(c_S-c0) + 2·A_part·c_S = 0 -> c_S = k_c·c0/(k_c+2A_part)
#
#   分配系数 k = c_S/c_L = k_c/(k_c + 2·A_part)
#   取 A_part = k_c/2  ->  k = 0.5（占位值，见下）
#
# 【注意：不用 ACGBPoly】
#   ACGBPoly 会额外往 η 方程里加一项 2·en_ratio·mu·gamma·η·c²。
#   【2026-09-18 ④ 修复后】`mu` 已改成**正常数**（见 [mu_barrier_const]），
#   所以"耦合强度随温度变号"这个理由已不成立。但溶质拖曳属于 Gate 1 第 8 项，
#   要单独验证（变分耦合 + 自由能耗散非增），所以**仍然先不加**。
#   代价：暂时没有溶质拖曳。
#
# 【溶质参数：2026-09-18 已换成 Ti64 真实值（缺口 #6 已补）】
#   1. 溶质取 **V（钒）**，c0 = 0.036（V 在 Ti64 中的原子分数，由 4 wt% 换算）。
#      为什么不取 Al：k_Al ≈ 0.98（几乎不偏析），而 V 是**主导偏析元素**。
#      **已知局限**：单组元化丢掉了 Al 的贡献（小）。若要更严格需升级为双组元。
#   2. 分配系数 **k = 0.63**（Lee et al. 2025 JMRT 36:3796；PanTi CALPHAD 一致）。
#      实现方式：free_energy 用 A_part = (k_c/2)*(1/k - 1) = 0.264。
#      **关系式 k = 1/(1 + 2*A_part/k_c) 已数值验证**（三组变体偏差均 <1%，
#      见 pipeline/verify_partition.i 与 ROADMAP §4.2）。
#   3. **扩散系数**：源码注释写 D = M*f'' = 2.8e-9*1.8 = 5e-9 m^2/s（2026-09-17 起）。
#      ⚠ **这个 1.8 对不上任何一处 f''**：f'' = k_c + 2*A*Sum(eta^2)，
#        液相 = 0.9、固相 = 1.428。⇒ **D 需要重新核定** —— 它直接决定
#        delta_c = D/V 与整个 Gate 1 的无量纲数 W/(D/V)。（2026-09-18 记）
#      但真实 LPBF 的溶质边界层 δ_c ~ D_L/V = 5e-9/0.6 ≈ 8 nm，
#      比 1 um 网格小两个数量级，**仍然不可能解析**。
#      所以这里解出的是"被网格展宽后"的溶质剖面，不是真实边界层。
#      物理上 LPBF 溶质几乎不扩散、存在明显**溶质截留** ——
#      定量时必须换模型（截留会让有效分配系数趋近 1）。
#      ⇒ 见 ROADMAP §4.3（C4）：MOOSE 有现成 AntitrappingCurrent，先测再决定。
#
# 【坑】同 stage1_meltpool.i：dtmax 必须限制、pi 不能在网格生成器里用、
#       symbol_values 不能是表达式。详见该文件的注释与 LPBF方案_单熔池.md。
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
    elem_type = QUAD4
  []
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
  [laser_T]
    type = ParsedFunction
    expression = 'min(353 + 28/(2*pi*20*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-0.6*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+x+1.2e-4-0.6*t)/(2*6e-06)), 3200)'
  []
[]

[Variables]
  [PolycrystalVariables]
  []
  # --- 溶质：c 是浓度，w 是化学势（分裂式 CH 用）---
  [c]
  []
  [w]
  []
[]

[ICs]
  [PolycrystalICs]
    [PolycrystalColoringIC]
      polycrystal_ic_uo = voronoi
      block = 0
    []
  []
  # 液相与固相初始都是名义成分（LPBF 熔池与基体同成分）
  # c0 = V 的原子分数 0.036（由 Ti64 的 4 wt% V 换算）
  [c_init]
    type = ConstantIC
    variable = c
    value = 0.036
  []
  [w_init]
    type = ConstantIC
    variable = w
    value = 0.0
  []
[]

[UserObjects]
  # 【2026-09-17 换成柱状晶基体】
  #   真实 LPBF 的基体**不是等轴多晶**，而是上一道/上一层留下的柱状晶。
  #   新熔池外延生长在这些柱状晶上 —— 它们本来就又长又取向一致，
  #   所以能继续向熔池内延伸。给等轴基体，再怎么外延也长不出柱状。
  #
  #   种子文件由 gen_columnar_seeds.py 生成：11 列、每列 1 个种子、列间距 40 um，
  #   于是 Voronoi 胞在 y 方向没有邻居 -> 贯穿全深（150 um），预期长宽比 ~3.8。
  #   设了 file_name 后 grain_num 被忽略（由文件行数决定）。
  [voronoi]
    type = PolycrystalVoronoi
    file_name = columnar_seeds.csv
    # 【2026-09-17 必须显式指定染色算法】
    # 用 file_name 时**默认算法会退化**：11 个种子全被染成同一个颜色，
    # 于是整个固态区变成 1 个晶粒（GrainTracker 报 1，Exodus 里 unique_grains 只有 {0}）。
    # 最小对照实验（5 个一行排列的种子）：
    #     grain_num=5             -> 5 个晶粒  ✓
    #     file_name（默认算法）    -> 1 个晶粒  ✗
    #     file_name + bt          -> 5 个晶粒  ✓
    coloring_algorithm = bt
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

[Kernels]
  # --- 溶质（分裂式 Cahn-Hilliard）---
  # 这套写法直接沿用 phase2_prod.i，已验证可跑
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    # 【必须】M 现在依赖 η ⇒ 不声明 gr0..gr7 的话，∂M/∂η_i 整块不进雅可比
    # （SplitCHWResBase.h:83 `_dmobdarg[cvar] = getMaterialPropertyDerivative(_mob_name, i)`，
    #  而 cvar 来自 mapJvarToCvar —— 只认声明过的耦合变量）。
    # 这是 P0-1 的同类缺陷，只是换了个核。
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w

    # =====================================================================
    # 【2026-09-19 修复 P15 / 审计 P0-1】必须声明 gr0..gr7
    # =====================================================================
    # f_loc 依赖 c **和** 全部 8 个序参量（见 [free_energy] 的
    # coupled_variables = 'c gr0 ... gr7'），但本核原先**一个都没声明**。
    #
    # ---- 后果（源码级，非推测）----
    # SplitCHParsed 的非对角雅可比是这么来的（SplitCHParsed.C）：
    #     _d2Fdcdarg[i] = getMaterialPropertyDerivative<Real>("f_name", _var.name(), i);
    #     computeQpOffDiagJacobian(jvar) -> (*_d2Fdcdarg[mapJvarToCvar(jvar)])[_qp]
    # 而 mapJvarToCvar 只会映射**声明过的耦合变量**。没声明 gr_i ⇒
    # ∂²f_loc/∂c∂η_i **整块不进入雅可比**（8 × 8 的子块）。
    #
    # 注意区分：**残差是对的，只有雅可比缺项**。所以在能收敛的前提下解不变，
    # 但牛顿收敛速率退化、预条件子失效——正是本项目反复栽的那类
    # "静默出错"（AGENTS.md §3.1）。
    #
    # ---- 已有的证据 ----
    # SplitCHParsed::initialSetup 里有
    #     validateNonlinearCoupling<Real>("f_name", _var.name());
    # 它只 **mooseWarning**（不报错），生产日志里一直在刷
    #     Missing coupled variables {gr0,...,gr7}
    # 这条告警此前被当成噪音，实际是真缺陷。**今后把这条告警当错误看。**
    #
    # ---- 为什么现在的写法能跑 ----
    # gdir_p/gdir_q（热梯度方向）是**非导数** ParsedMaterial（见生成器 2b 段），
    # 它们以"数据"身份进入 align4，所以 ∂f_loc/∂η_i 里不含 ΔT 的导数项——
    # 这也是当初"关掉 2b 就收敛"那个实验真正在测的东西。
    #
    # ---- 修复的边界（审计明确要求）----
    # 只加这一行。**不得**同时改 M、kappa_c、自由能形式、网格或时间步——
    # 否则"修复前后"的对照无法归因（AGENTS.md §3.3 教训 12）。
    # 修复前后必须做 -snes_test_jacobian 与 解/牛顿迭代数/守恒 三项对照，
    # 见 validated/jacobian_test.sh。
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
  []

  # ===========================================================================
  # 【④ 修复 2026-09-18】Landau 二次项驱动力 —— 每个序参量一个 AllenCahn
  # ===========================================================================
  # 它们与 GrainGrowth action 生成的 ACGrGrPoly **相加**，合起来正好是
  # Landau 自由能 f_新 对 η_i 的导数（推导见 [Materials] 里 [barrier_muT] 段）：
  #     ACGrGrPoly(mu=const mu0)   →  mu0·(η³ − η + 2γηΣ)
  #     + AllenCahn(f_drive)       →  (mu0 − mu_T)·η_i
  #     = mu0·η³ − mu_T·η + 2·mu0·γηΣ   ✓
  #
  # 【为什么用 AllenCahn 而不是 MatReaction】
  #   AllenCahn 的雅可比是**符号完备**的（AllenCahn.C:52 对角 ∂²F/∂η²、
  #   :65 非对角 ∂²F/∂η∂η_j、ACBulk.h:105 迁移率乘积法则项）。
  #   MatReaction 只对**已声明**的参数求导（MatReaction.C:96-109），
  #   缺失的导数会**静默取 0** —— 正是本项目 D 版不收敛栽过的那类坑。
  #
  # 【coupled_variables 必须写全其余 7 个】
  #   因为 L 是各向异性的、对全部 8 个序参量都有导数（生成器的 L2b），
  #   ACBulk::initialSetup 的 validateNonlinearCoupling("mob_name")
  #   会检查 L 的耦合变量是否都在本核的耦合集里，缺了会告警且
  #   _dLdarg[i] 少项（雅可比不完备）。
  [gr0_drive]
    type = AllenCahn
    variable = gr0
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr1 gr2 gr3 gr4 gr5 gr6 gr7'
  []
  [gr1_drive]
    type = AllenCahn
    variable = gr1
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr2 gr3 gr4 gr5 gr6 gr7'
  []
  [gr2_drive]
    type = AllenCahn
    variable = gr2
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr3 gr4 gr5 gr6 gr7'
  []
  [gr3_drive]
    type = AllenCahn
    variable = gr3
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr2 gr4 gr5 gr6 gr7'
  []
  [gr4_drive]
    type = AllenCahn
    variable = gr4
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr2 gr3 gr5 gr6 gr7'
  []
  [gr5_drive]
    type = AllenCahn
    variable = gr5
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr6 gr7'
  []
  [gr6_drive]
    type = AllenCahn
    variable = gr6
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr7'
  []
  [gr7_drive]
    type = AllenCahn
    variable = gr7
    f_name = f_drive
    mob_name = L
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6'
  []
[]

[Modules]
  [PhaseField]
    [GrainGrowth]
      # L 依赖 T -> 必须 variable_mobility = true 并把 T 传进去
      variable_mobility = true
      coupled_variables = 'T'
      mobility = L
      kappa = kappa_op
      # 【注意】这里**不设 c**，即不启用 ACGBPoly，理由见文件头
    []
  []
[]

[Materials]
  # 【2026-09-17 同步 Ti64 参数】
  #   sigma = 0.6 J/m^2 (Gornakova & Prokofjev 2020)
  #   mu0   = 6*sigma/wGB   = 9.0e5
  #   kappa = 0.75*sigma*wGB = 1.8e-6
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'kappa_op  gamma_asymm'
    prop_values = '1.8e-6    1.5'
  []

  # 【2026-09-17 同步 Arrhenius】晶界迁移率 L 改为温度相关
  #   M_GB = GBmob0*exp(-Q/(kb*T))，L = 4/3*M_GB/wGB
  #   Ti64 beta: GBmob0 = 232 m^4/(J*s), Q = 3.234 eV
  #   （出处见 stage1_meltpool_ti64.i 的详细注释）
  #   **M0 与 Q 必须成对替换**，只换一个一定错。
  [L_mobility]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T'
    constant_names = 'GBmob0 Q kb wGB'
    constant_expressions = '232 3.234 8.617e-5 4.0e-6'
    expression = '4.0/3.0 * GBmob0 * exp(-Q/(kb*T)) / wGB'
    derivative_order = 1
  []

  # ===========================================================================
  # 【④ 修复 2026-09-18】熔化开关：从「势垒系数」改成「二次项系数」(Landau)
  # ===========================================================================
  #
  # ---- 原形式为什么病态 ----
  #   ACGrGrPoly.C:61 的残差是 mu*(η³ − η + 2γ·η·Σ_{j≠i}η_j²)，对应
  #       f_旧 = mu(T)·[ Σ(η⁴/4 − η²/2) + γ Σ_{i<j} η_i²η_j² ]
  #   mu 同时乘四次项与二次项。液相里 mu(T) < 0，于是：
  #     (a) 四次项系数变号  ⇒ f 在 η→∞ 时 → −∞      **自由能下无界**
  #     (b) 交叉项变吸引    ⇒ 相邻序参量互相上拉       **η 冲过 1 停不下来**
  #   实测（tests/make_melt_ab.py，mu = −2·mu0，1D 晶界）：
  #     η 冲到 786，Ση² 冲到 4.6e5，min F = −6.07e10，
  #     34 步里 27 步牛顿 DIVERGED_LINE_SEARCH 后 MPI_Abort。
  #
  # ---- 新形式：标准 Landau 展开，温度只进二次项 ----
  #       f_新 = mu0·Σ(η⁴/4) − mu_T(T)·Σ(η²)/2 + mu0·γ Σ_{i<j} η_i²η_j²
  #       ∂f_新/∂η_i = mu0·η_i³ − mu_T·η_i + 2·mu0·γ·η_i·Σ_{j≠i}η_j²
  #
  # ---- 怎么实现（与 GrainGrowth action 并存，改动最小）----
  #   ACGrGrPoly 取**常数** mu = mu0   →  mu0·(η³ − η + 2γηΣ)
  #   再加 AllenCahn(f_drive)          →  (mu0 − mu_T)·η_i
  #   两项相加 = mu0·η³ − mu_T·η + 2·mu0·γηΣ   ✓ 正是 ∂f_新/∂η_i
  #
  # ---- 性质（可证，非调参）----
  #   * 驻点：  η_i² = mu_T/mu0 − 2γ·Σ_{j≠i}η_j²  ≤  s ≡ mu_T/mu0
  #     mu_T = mu0·(1 − 1.5(1+tanh)) ∈ [−2mu0, mu0] ⇒ s ≤ 1 ⇒ **η ≤ 1 恒成立**
  #     ⇒ 原模型的越界在数学上不可能再出现
  #   * 四次项与交叉项系数恒正 ⇒ f 有界 ⇒ 模型良定
  #   * mu_T = mu0（T 足够低）时与 f_旧 **逐项恒等** ⇒ 固相物理不变
  #     （回归验证：tests/grain_growth_ac.i vs tests/grain_growth_circle.i）
  #   * 熔化温度不变：mu_T 过零仍在 T = 1882.2 K（tanh = −1/3）
  #   * **额外收益**：势垒系数变成常数 9e5 ⇒ 生成器按 μ=9e5 解出的
  #     Moelans 不动点 (a*, γ*) 与 κ/(γ·) 在**全域**自洽。
  #     原模型里 μ(T) 在热区偏离 9e5，而 σ ∝ sqrt(μ) —— 即热区的
  #     各向异性晶界能其实是错的。本修复顺手消掉了这个隐患。
  #   * 代价（必须知道，列进 Gate 2 标定）：σ(T) 仍随温度降，但改为
  #     Landau 的 σ ∝ s（原模型 ∝ sqrt(s)）⇒ T=1830 K 时 σ 由
  #     0.5224 → 0.4548 J/m²（−13%）。这是**重新标定项，不是自由参数**。
  [barrier_muT]
    type = DerivativeParsedMaterial
    property_name = mu_T
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
  []

  # ACGrGrPoly 的势垒系数：**正常数** mu0（不再随 T 变号）。
  # ⚠ 必须逐位等于 [barrier_muT] 的 mu0，也等于生成器的 MU_QP = 6*sigma_H/wGB。
  #   run_nonad_prod.sh 有断言同时核对这三处。
  [mu_barrier_const]
    type = GenericConstantMaterial
    prop_names  = 'mu'
    prop_values = '9.0e5'
  []

  # Landau 的二次项驱动力  f_drive = (mu0 − mu_T)/2 · Ση_i²
  #   ⇒ ∂f_drive/∂η_i = (mu0 − mu_T)·η_i   （正是 ACGrGrPoly 与 Landau 之差）
  # 用 AllenCahn 消费：符号求导 ⇒ 对角 ∂²/∂η_i² = (mu0−mu_T)，
  # 非对角 ∂²/∂η_i∂η_j = 0（f_drive 是平方和）—— 两者都精确，无手写雅可比。
  # ⚠ mu0/mu_T 走 material_property_names（不是 coupled_variables）：
  #   这样 f_drive 只耦合 8 个序参量，AllenCahn 的耦合校验才成立，
  #   且 T（AuxVariable）不进入雅可比。
  [f_drive]
    type = DerivativeParsedMaterial
    property_name = f_drive
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'mu mu_T'
    expression = '0.5*(mu-mu_T)*(gr0^2+gr1^2+gr2^2+gr3^2
                                +gr4^2+gr5^2+gr6^2+gr7^2)'
    derivative_order = 2
  []

  # --- 溶质参数（已重标定）---
  #
  # 【2026-09-17 重标定，修 SUBPC_ERROR】把自由能除以 F0 = 1e6：
  #     f -> f/F0,  w -> w/F0,  kappa_c -> kappa_c/F0,  M -> M*F0
  #   物理**完全不变**（D = M*f'' 不变、分配系数 k 不变），
  #   但雅可比矩阵的量级大幅改善。
  #
  #   起因：分裂式 CH 的矩阵量级悬殊 ——
  #       w 行对角   = M/dx^2 = 2.8e-3
  #       w 行非对角 = 1/dt   = 1e7
  #   差 10 个数量级，ILU 子域分解直接崩（SUBPC_ERROR -> NANORINF），
  #   自适应步长被砍到 3e-8，时间几乎推不动。
  #   重标定后 M/dx^2 = 2.8e3，比值 3.6e9 -> 3.6e3；**步长立刻恢复到 2e-6**。
  #
  #   扩散系数：D = M*f'' = 2.8e-9 * 1.8 = 5.0e-9 m^2/s
  #             **恰好是 Ti 的液相扩散系数**（原来被放大 8 倍）
  #   c 的界面宽：w_c = sqrt(kappa_c/f'') ——【2026-09-18 Gate 1 修正后】
  #     旧 kappa_c=1.125e-11 -> w_c = 2.5 um，**比晶界宽 d=2 um 还大**
  #     新 kappa_c=1e-14     -> w_c = 0.105 um = d/19   （见下面 [ch_params] 的详细说明）
  #
  #   代价：溶质扩散长度 sqrt(D*t) 在 t=8e-4 s 时约 2 um，剖面很锐 ——
  #   这反而更接近 LPBF 的真实情形（真实溶质边界层只有 ~8 nm）。
  # 【2026-09-18 Gate 1 修正】kappa_c: 1.125e-11 -> 1e-14
  #
  # 为什么改：c 的界面宽 w_c = sqrt(kappa_c/k_c) 必须**远小于** η 的界面宽
  # （本算例 d = sqrt(2*kappa_op/mu0) = 2.00 um），否则溶质剖面跟不上 η，
  # 平衡关系 c = c0*k_c/(k_c+2A*eta^2) 不再是平衡态 —— **分凝被抹平**。
  #
  #   旧值 1.125e-11 -> w_c = 3.54 um  >  d = 2.00 um     判据要求 w_c << d，**违反**
  #   新值 1e-14     -> w_c = 0.105 um = d/19              ✓
  #
  # 静止界面控制实验实测（生产几何、生产网格 dx=1um）：
  #   kappa_c = 1.125e-11  ->  k_eff = 0.6796  (偏差 +7.82%)
  #   kappa_c = 1e-14      ->  k_eff = 0.6354  (偏差 +0.81%)   ← 达标（判据 <2%）
  #   kappa_c = 1e-16      ->  k_eff = 0.6354  (同上，已收敛)
  #   平衡值 = 1/(1+2*A_part/k_c) = 0.6303
  #
  # ⚠ **verify_partition.i 当初验证 k=0.630 时用的是 kappa_c=1e-14、M=1e-6，
  #    不是生产值** —— 所以生产的分配系数从未在其自身的 kappa_c 下被验证过。
  #    这是 Gate 1 2026-09-18 发现并修掉的缺口。
  #
  # kappa_c 可以自由减小的理由：晶界能由 kappa_op/mu 决定，kappa_c 只是 c 场的
  # 正则化项；减小它还会让分裂式 CH 的 4 阶刚度下降（更稳）。无物理副作用。
  # =====================================================================
  # 【Phase 1.3】溶质迁移率分层：D_L / D_S / D_GB（审计 P0-3 + P0-4）
  # =====================================================================
  # 改前：M = 2.8e-9 常数，于是 D = M·f_cc，而 f_cc = k_c + 2·A_part·Ση²：
  #     液相 (Ση²=0)      D = 2.52e-9
  #     固相 (Ση²=1)      D = 4.00e-9   <- **比液相还快 1.59 倍（物理上反了）**
  #     固固晶界(Ση²=0.5)  D = 3.26e-9   <- 没有独立的晶界快速通道
  # 真实 Ti64 中 V 的 D_L 比 D_S 高约 4 个数量级，D_GB 又比 D_S 高若干个数量级。
  #
  # ---- 指示函数的选取（这里踩过一个坑，必须记下来）----
  # 第一版草稿用的是 h_gb = 4·S·(1−S)（S = Ση_i²）。
  # 它有个致命缺陷：**固液界面中点也满足 S ≈ 0.5**，于是固液界面会被
  # 误判成晶界，拿到 D_GB 的快速扩散 —— 而 LPBF 里恰恰是固液界面最重要。
  # 用 check_D_layering.py 与代码核对时发现了（晶界态算出 1.66e-9 而不是 4e-10）。
  #
  # 正确的晶界指示必须能区分「**两个不同晶粒**相遇」与「固相遇到液相」：
  #     固液界面：只有 1 个 η 非零        -> 指示 = 0
  #     固固晶界：2 个 η 同时非零          -> 指示 = 1
  # 用配对乘积即可：
  #     h_gb = 16 · Σ_{i<j} η_i² η_j² = 8·(S² − Q),   Q = Σ η_i⁴
  #   二元晶界 (η₀=η₁=0.5)：S=0.5, Q=0.125 -> 8·(0.25−0.125) = 1  OK
  #   晶粒内部 (η₀=1)      ：S=1,   Q=1     -> 0                  OK
  #   液相                 ：S=0             -> 0                  OK
  #   固液界面             ：只有 1 个 η     -> 0                  OK  <- 关键
  #   三叉晶界 (各 1/3)     ：S=1/3, Q=1/27  -> 16/27 ≈ 0.593      OK
  #
  # 固相指示：晶界处 S 只有 0.5，直接用 S 会让液相项漏进来（D 偏大）。
  #     h_s = min(1, 2·S)
  #   晶界 -> min(1,1) = 1；晶粒内 -> 1；液相 -> 0；固液界面 -> 2S（线性混合）
  #
  #   ⚠ 第一版用的是 h_s = S + h_gb(1−S)。它在**晶界两翼**把液相项漏进了固相，
  #     而且这一点是**用 1D 晶界算例量出来的**（validated/make_1d_gb.py），
  #     不是推出来的：
  #         位置           S       h_gb    h_solid    D (m²/s)      D/D_S
  #         晶粒 x=0.2µm  0.9998   0.000    0.9998    1.02e-12       2.6×
  #         晶粒 x=0.6µm  0.9982   0.000    0.9982    4.99e-12      12×
  #         晶粒 x=1.4µm  0.9096   0.033    0.9126    2.34e-10     584×
  #         晶界两翼      0.6068   0.619    0.8501    6.26e-10   ← 比晶界中心还大！
  #         晶界中心      0.5000   1.000    1.0000    4.00e-10
  #     **D 的最大值跑到了晶界两侧**，物理上反了；固相里 D 比 D_S 大 2.6~584 倍。
  #     根因：D_L 与 D_S 相差 6300 倍时，(1−h_solid) 的尾巴被放大 6300 倍。
  #     ⇒ 固相指示**必须在晶界处正好等于 1**。
  #   min(1, 2S) 在 S=0.5（二元晶界中点）恰好饱和到 1，两翼也全是 1。
  #   修复后实测：固相 D = 4.009e-13（期望 D_S=4.0e-13，+0.24%），
  #               且 D 随远离晶界**单调下降**。
  #   ⚠ 代价：min() 在 S=0.5 处有一个导数拐点（正好落在二元晶界中心线上）；
  #     MOOSE 对 min() 取次梯度，实测牛顿正常收敛。
  #
  # 合成：
  #     D(η) = D_L + (D_S−D_L)·h_s + (D_GB−D_S)·h_gb
  #   三个极限分别精确给出 D_L / D_S / D_GB —— 可逐点核对（T6）。
  #
  # =====================================================================
  #     M    = D(η) / f_cc,     f_cc = k_c + 2·A_part·S
  # =====================================================================
  # **关键性质**：f_cc 就是 f_loc 对 c 的二阶导（f_loc 是 c 的二次多项式），
  # 所以由构造保证 D = M·∂²f/∂c² 逐点成立。
  #
  # ⚠⚠ 参数来源：Ti64 中 V 的 D_S、D_GB 定量数据**基本不存在**（本项目已知
  #    文献缺口）。以下数值一律是 **calibration 参数**，不是材料常数。
  #    **不得**在任何文档或论文里写成"已验证的 Ti64 数据"。
  #
  # ⚠ M 现在依赖 η ⇒ [Kernels]/[coupled_res] **必须**声明 gr0..gr7，
  #    否则 ∂M/∂η_i 整块不进入雅可比 —— 与 P0-1 完全同类。
  #     本脚本已同步打上那个补丁。
  # =====================================================================
  [ch_kappa]
    type = GenericConstantMaterial
    prop_names  = 'kappa_c'
    prop_values = '1e-14'
  []

  # --- S = Ση²（固相指示 + f_cc 的输入）---
  [solute_S]
    type = DerivativeParsedMaterial
    property_name = S_eta2
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = 'gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2'
    derivative_order = 2
  []

  # --- Q = Ση⁴（只为算 h_gb）---
  [solute_Q]
    type = DerivativeParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = 'gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4'
    derivative_order = 2
  []

  # --- 晶界指示 h_gb = 8(S²−Q) = 16·Σ_{i<j}η_i²η_j²；二元晶界=1，其余=0 ---
  [solute_hgb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []

  # --- 固相指示 h_s = min(1, 2S)；晶界处饱和到 1 ---
  [solute_hs]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
    derivative_order = 2
  []

  # --- 分层扩散系数 -> 迁移率 M = D(η)/f_cc ---
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2 h_gb h_solid'
    constant_names = 'D_L D_S D_GB k_c A_part'
    constant_expressions = '2.52e-09 4e-13 4e-10 0.9 0.264'
    expression = '(D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb) / (k_c + 2*A_part*S_eta2)'
    derivative_order = 2
  []

  # 溶质自由能：给出液相/固相分凝
  # 【分配系数的实现方式】平衡时固液两相 μ = ∂f/∂c 相等，解得
  #     k = c_S/c_L = 1/(1 + 2*A_part/k_c)
  #   反解即 A_part = (k_c/2)*(1/k - 1)。
  #   **该关系式已数值验证**（三组变体偏差均 <1%）：见 pipeline/verify_partition.i。
  #   现值：k_c=0.9, c0=0.036（V 原子分数）, A_part=0.264 -> k = 0.630（Ti64 的 V）
  #   k_c 与 F0 同步缩放过（9.0e5 -> 0.9）。
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '0.9 0.036 0.264'
    expression = 'k_c/2*(c-c0)^2
                  + A_part*c^2*(gr0^2+gr1^2+gr2^2+gr3^2
                                +gr4^2+gr5^2+gr6^2+gr7^2)'
    derivative_order = 2
  []

  # ===========================================================================
  # 【Gate 0 步骤 2c】晶粒体自由能 —— 纯诊断用，不参与任何方程
  # ===========================================================================
  #
  # 来源：从 MOOSE 源码反推
  #     modules/phase_field/src/kernels/ACGrGrPoly.C:61
  #     return _mu[_qp] * (op*op*op - op + 2.0*_gamma[_qp]*op*SumOPj);
  #                                                   // SumOPj = Σ_{j≠i} η_j²
  # 反推得（要求 ∂f/∂ηᵢ = mu·(ηᵢ³ − ηᵢ + 2γ·ηᵢ·Σ_{j≠i}ηⱼ²)）：
  #
  #     f_grain = mu·[ Σᵢ(ηᵢ⁴/4 − ηᵢ²/2) + γ·Σ_{i<j} ηᵢ²ηⱼ² ]
  #
  #   （等价形式 Σᵢ(ηᵢ⁴/4−ηᵢ²/2) + (γ/2)·Σ_{i≠j}ηᵢ²ηⱼ²，因 Σ_{i≠j} = 2Σ_{i<j}。
  #     **交叉项系数是 γ/2 不是 γ** —— 这里用的是 Σ_{i<j} 写法，系数即 γ。）
  #
  # 【已验证，机器精度通过】pipeline/tests/run_verify_f_grain.py：
  #     数值 dF/dη₀ 与 ∫(ACGrGrPoly.C:61 逐字转录) dV 相对误差 2.6e-14。
  #     （f_grain 对 η₀ 是四次多项式，四点中心差分对其**精确**，故不是"近似吻合"。）
  #     ⇒ 改动本表达式后**必须重跑该验证**，否则不得用于诊断。
  #
  # ⚠ 【R2：绝对零点未知】MOOSE 的残差只约束 ∂f/∂η，f 本身可差一个常数。
  #    ⇒ **只用于比较与耗散检查（非增），不得用于绝对数值。**
  #
  # ⚠ 【2026-09-18 ④ 修复后本条已改变】
  #    旧： f_grain = mu(T)·[Σ(η⁴/4−η²/2) + γΣη²η²]，液相内 mu<0 ⇒ **下无界**。
  #    新： f_grain = mu·Σ(η⁴/4) − mu_T·Σ(η²)/2 + mu·γ·Σ_{i<j}η²η²（mu = 常数 mu0）
  #    它是 ACGrGrPoly(mu=mu0) 与 f_drive 两者自由能之和，恒有界：
  #      四项系数(四次+交叉)恒正 ⇒ η→∞ 时 f→+∞；驻点处 η_i² ≤ mu_T/mu0 ≤ 1。
  #    所以 **"F 非增"判据现在在熔化阶段也应成立**（旧版只在全固相时成立）。
  #    这条从"已知局限"升级为"可检验的判据"，已列入 Gate 1 第 8 项。
  #
  # ⚠ 【本材料不产生雅可比项】没有任何 kernel 消费 f_grain，它只被后处理器读取。
  #    真正进方程的是 ACGrGrPoly(mu) + f_drive 两者之和，与这里的表达式**恒等**。
  #    这是"诊断量与模型一致"的设计：两处若漂移，F_grain 的耗散判据立刻失真。
  [f_grain]
    type = DerivativeParsedMaterial
    property_name = f_grain
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'mu mu_T gamma_asymm'
    expression = 'mu*(
                    gr0^4/4+gr1^4/4+gr2^4/4+gr3^4/4
                   +gr4^4/4+gr5^4/4+gr6^4/4+gr7^4/4
                   +gamma_asymm*(
                      gr0^2*gr1^2+gr0^2*gr2^2+gr0^2*gr3^2+gr0^2*gr4^2+gr0^2*gr5^2+gr0^2*gr6^2+gr0^2*gr7^2
                     +gr1^2*gr2^2+gr1^2*gr3^2+gr1^2*gr4^2+gr1^2*gr5^2+gr1^2*gr6^2+gr1^2*gr7^2
                     +gr2^2*gr3^2+gr2^2*gr4^2+gr2^2*gr5^2+gr2^2*gr6^2+gr2^2*gr7^2
                     +gr3^2*gr4^2+gr3^2*gr5^2+gr3^2*gr6^2+gr3^2*gr7^2
                     +gr4^2*gr5^2+gr4^2*gr6^2+gr4^2*gr7^2
                     +gr5^2*gr6^2+gr5^2*gr7^2
                     +gr6^2*gr7^2
                   ))
                  - mu_T/2*(gr0^2+gr1^2+gr2^2+gr3^2
                           +gr4^2+gr5^2+gr6^2+gr7^2)'
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

  # --- 溶质守恒：这是核心检查，必须漂到机器精度（对比 phase0a 的结论）---
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
  # 固相平均浓度 vs 液相平均浓度 —— 直接看分凝有没有建立
  [c_solid_avg]
    type = ElementAverageValue
    variable = c
    block = 0
    execute_on = 'initial timestep_end'
  []
  [dt]
    type = TimestepSize
  []

  # ===========================================================================
  # 【Gate 0 步骤 2d】诊断后处理器
  #
  # ⚠ 全部显式设 execute_on = timestep_end —— 实测 t=0 那一行后处理器**全为 0**
  #   （材料尚未求值），若用 initial 会把所有量读成 0，看起来像灾难性 bug。
  #   实测证据：/tmp/t4.i 与 tests/verify_f_grain_out.csv 的 `0,0,0,0,0,0,0` 行。
  # ===========================================================================

  # --- 自由能（只增不改，f_grain 的定义见 [Materials] 里的长注释）---
  [F_loc]
    type = ElementIntegralMaterialProperty
    mat_prop = f_loc
    execute_on = timestep_end
  []
  [F_grain]
    type = ElementIntegralMaterialProperty
    mat_prop = f_grain
    execute_on = timestep_end
  []

  # --- 序参量越界检查：每个 gr_i 的最大值应 <= 1 ---
  #   用 NodalExtremeValue（序参量是 Lagrange，节点量）。
  [gr0_max]
    type = NodalExtremeValue
    variable = gr0
    value_type = max
    execute_on = timestep_end
  []
  [gr1_max]
    type = NodalExtremeValue
    variable = gr1
    value_type = max
    execute_on = timestep_end
  []
  [gr2_max]
    type = NodalExtremeValue
    variable = gr2
    value_type = max
    execute_on = timestep_end
  []
  [gr3_max]
    type = NodalExtremeValue
    variable = gr3
    value_type = max
    execute_on = timestep_end
  []
  [gr4_max]
    type = NodalExtremeValue
    variable = gr4
    value_type = max
    execute_on = timestep_end
  []
  [gr5_max]
    type = NodalExtremeValue
    variable = gr5
    value_type = max
    execute_on = timestep_end
  []
  [gr6_max]
    type = NodalExtremeValue
    variable = gr6
    value_type = max
    execute_on = timestep_end
  []
  [gr7_max]
    type = NodalExtremeValue
    variable = gr7
    value_type = max
    execute_on = timestep_end
  []

  # --- 求解代价（直接进 CSV，**不需要解析 run.log**）---
  #   实测：NumNonlinearIterations / NumLinearIterations 是现成后处理器，
  #   见 framework/src/postprocessors/。这是对"解析日志"方案的重要改进。
  [n_elem]
    type = NumElements
    execute_on = timestep_end
  []
  [n_nonlin]
    type = NumNonlinearIterations
    execute_on = timestep_end
  []
  [n_lin]
    type = NumLinearIterations
    execute_on = timestep_end
  []
[]

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

  # 【2026-09-17 修死配置】原来最后一项写的是 -sub_pc_asm_overlap，
  # PETSc 3.25 不认这个名字（日志里报 "Option left: name:-SUB_PC_ASM_OVERLAP"），
  # 一直**被静默忽略** —— 也就是说预条件子的重叠层数根本不是我们以为的 1。
  # 正确名字是 -pc_asm_overlap。
  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'
  petsc_options_value = 'asm      31                  preonly       ilu          1'

  # 【Gate 0 步骤 2a】线性迭代上限 30 -> 300。
  #   依据：生产脚本 run_nonad_prod.sh 的实测记录「非 AD + l_max_its=300 是零失败，
  #   AD + 300 有 2 次 DIVERGED_ITS」——30 太小，ASM/ILU 下外 GMRES 需要更多迭代。
  #   【审2】要求"按实际收敛日志设置"，故档 A 回归后仍需用 n_lin 的实际分布复核。
  l_max_its = 300
  l_tol = 1e-6
  nl_max_its = 50
  nl_rel_tol = 1e-8
  # 【Gate 0 步骤 2a】非线性绝对容差 1e-7 -> 1e-9（两份专家评审一致要求）。
  #   已实测：非 AD + MUMPS 能**二次收敛到 4.01e-10**，所以 1e-9 是可达的。
  #   ⚠ 旧的「非 AD 有 7.3e-07 残差地板」归因**已被实测推翻**——
  #     地板来自 ASM/ILU 预条件子，不是 Jacobian 不完备。
  #     **不得**据此把 nl_abs_tol 放宽回 1e-6。
  nl_abs_tol = 1e-9

  end_time = 6.5e-4

  # 【关键】界面弛豫时间 ~4.7e-6 s；不加 dtmax 会发散。
  # 【Gate 0 步骤 2a】**本值不动**——两份专家评审都明确要求不要放宽到 4e-6，
  # 除非有新的能量稳定性实验支持。
  dtmax = 2e-6

  [TimeStepper]
    type = IterationAdaptiveDT
    # 【Gate 0 步骤 2a】起始步长 1e-6 -> 1e-7。
    #   实测：给 1e-6/4e-6 会让首步反复失败（全尺寸白烧 47 分钟）。
    #   注意 dtmax 不动（见下），两者是不同的约束。
    dt = 1e-7
    cutback_factor = 0.5
    growth_factor = 1.5
    # 【2026-09-17】含溶质后每步的牛顿迭代数明显变多，
    # optimal_iterations=5 太严 —— 实测步长在 3e-8~7.5e-8 之间锯齿
    # （涨 1.5x 就被砍回 0.5x），时间几乎推不动。
    # 放到 10 让自适应步长能涨起来。
    optimal_iterations = 10
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  [exo]
    type = Exodus
    # 【每一步都存】面拓扑每步都在变，隔步存会漏掉大部分拓扑事件，
    # 而转移算子正是靠这些事件训练的。文件大不是问题（存在 F 盘）。
    # 【2026-09-18 用户决定】取 1，每一步都保存。
    time_step_interval = 1
    file_base = stage1c
  []

  # ===========================================================================
  # 【Gate 0 §9.1】检查点：改成**按步数**存，不再按墙钟
  # ===========================================================================
  # 为什么必须加这一段：
  #   全尺寸跑两次被**外部 SIGKILL**（退出码 137，非 OOM、非 WSL 重启、原因未定），
  #   而 `Checkpoint` 把 `wall_time_interval` 默认成 **3600 s** ——
  #   对 ~4.5 min/步 的全尺寸跑来说等于**1 小时才存一次**，
  #   被杀一次最多丢 1 小时机时。老生产跑 5 小时只留下 2 个检查点
  #   （N_out_cp/0066 与 0090），就是这个原因。
  #
  # ⚠ 必须**显式**写 time_step_interval：
  #   Output.C:138-141 的逻辑是
  #       (wall_time_interval 被用户设过 && time_step_interval 没被用户设过)
  #           ? 无限大 : time_step_interval
  #   所以只设 wall_time_interval 是无效的，必须设这一个。
  #
  # 续跑：phase_field-opt -i N.i --recover
  #   （不带参数则用最近的 recovery 文件；见 `--help`）
  [checkpoint]
    type = Checkpoint
    time_step_interval = 10
    num_files = 3
  []
[]
