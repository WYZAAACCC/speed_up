# =============================================================================
# Gate 1 · 步骤 0：1D 平面凝固前沿基准（模式 b —— 全场均匀温度 + 驱动力）
# =============================================================================
#
# 【为什么用模式 b 而不是冻结温度梯度】
#   冻结梯度模式下 μ(T) 随空间变，而界面宽 sqrt(2κ/μ) 在 μ→0 处**发散**
#   ⇒ W 无定义 ⇒ W/(D/V) 这个无量纲数失去意义。
#   本算例温度**全场均匀**，μ = Wg 恒定 ⇒ 界面宽 xi = sqrt(8κ/Wg) 良定义。
#
# 【自由能】—— η 与 c **共用同一个 F**（= 变分耦合）
#   F = Wg·η²(1−η)²/4  +  dG·h(η)  +  k_c/2·(c−c0)²  +  A·c²·η²
#       └─双势阱──┘      └驱动力┘     └──溶质──┘      └─分凝耦合─┘
#   h(η) = η³(10 − 15η + 6η²)   标准插值函数，h(0)=0, h(1)=1
#
#   ⇒ η=0 液相，η=1 固相；dG < 0 使固相自由能更低 ⇒ 前沿向液相推进。
#
#   **与生产模型的区别（这点很重要）**：生产的 A·c²·Ση² 只进了 c 方程
#   （f_loc），没进 η 方程（f_grain），所以**不是变分的**（源码自述"暂时没有溶质拖曳"）。
#   本算例两者统一 ⇒ 同时就是 Gate 1 第 8 项（拖曳验证）的载体。
#
# 【参数】
#   双势阱:  xi = sqrt(8κ/Wg) = 2.000 µm,  σ = sqrt(κWg)/(3√8) = 0.6000 J/m²
#            κ = 3.6e-6,  Wg = 7.2e6
#   溶质  :  k_c = 0.9, A = 0.264 (⇒ k = 0.6303), c0 = 0.036, M = 2.8e-9
#            D_L = M·k_c = 2.52e-9 m²/s
#   驱动力:  dG = −3.6e5  (Wg 的 5%，保双势阱完整)
#   ★ 前沿速度的正确关系（AC 方程乘 dη/dx 后积分）：
#        −v·∫(dη/dx)²dx = −L·ΔF ,  ∫(dη/dx)²dx = 1/(3ξ)
#     ⇒  v = 3·ξ·L·ΔF      ← **不是** v = L·ΔF（漏 3ξ 会让速度差 6 个数量级）
#     L = 5.833e-4 ⇒ v = 3*2e-6*5.833e-4*3.6e5 = 1.26e-3 m/s ✓
#   工作点:  s = W/(D/V) = 1  ⇒  δ_c = D/V = 2 µm,  V = 1.26e-3 m/s
#
# 【初值：解析稳态，无瞬态】
#   固相 (x < x0):  c = c0                      （稳态下固相均匀）
#   液相 (x > x0):  c = c0·[1 + (1−k)/k·exp(−V(x−x0)/D)]
#      ⇒ 界面处 c_l = c0/k，远端 → c0
#   若模型定量正确，该剖面应**自相似地平移**，且 k_eff = c_s/c_l = 0.6303
#
# 【用法】
#   bash run_checked.sh front1d.i Mesh/nx=160 Executioner/end_time=8e-3
#   ⚠ 并发跑必须各自独立目录（CSV 按输入文件名命名，会互相覆盖）
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 160
  xmin = 0.0
  xmax = 4.0e-5
[]

[GlobalParams]
  # 常数在 [Functions] 里统一给出，便于 CLI 覆盖做扫描
[]

[Variables]
  [eta]
  []
  [c]
  []
  [w]
  []
[]

[Functions]
  # 界面初始位置 x0 = 5 µm
  [eta_ic]
    type = ParsedFunction
    expression = '0.5*(1-tanh((x-5.0e-6)/2.0e-6))'
  []
  # 解析稳态溶质剖面（见文件头）
  [c_ic]
    type = ParsedFunction
    expression = 'if(x<5.0e-6, 0.036,
                    0.036*(1 + (1-0.6303)/0.6303*exp(-1.26e-3*(x-5.0e-6)/2.52e-9)))'
  []
[]

[ICs]
  [eta_ic]
    type = FunctionIC
    variable = eta
    function = eta_ic
  []
  [c_ic]
    type = FunctionIC
    variable = c
    function = c_ic
  []
  [w_ic]
    type = ConstantIC
    variable = w
    value = 0.0
  []
[]

[Kernels]
  # --- 相场（Allen-Cahn）---
  [eta_dot]
    type = TimeDerivative
    variable = eta
  []
  [eta_bulk]
    type = AllenCahn
    variable = eta
    f_name = F
    mob_name = L
    # 【必须】F 依赖 c（A*c^2*eta^2 那一项）⇒ 不声明 c 的话
    # ∂(eta 方程)/∂c 整块不进雅可比。与审计 P0-1 完全同类。
    # 判据来源：MOOSE 只在**声明过**的耦合变量上组装非对角项
    # （JvarMapInterface 的 _jvar_map，未声明者在
    #  JvarMapKernelInterface::computeOffDiagJacobian 里被静默 return 掉）。
    coupled_variables = 'c'
  []
  [eta_iface]
    type = ACInterface
    variable = eta
    kappa_name = kappa_op
    mob_name = L
  []

  # --- 溶质（分裂式 Cahn-Hilliard，与生产一致）---
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
    f_name = F
    kappa_name = kappa_c
    w = w
    # 【必须】F 依赖 eta ⇒ 同理，∂²F/∂c∂eta 不进雅可比会静默丢项。
    # 这条同时是 T1 的判据「无 Missing coupled variables」的直接对应项。
    coupled_variables = 'eta'
  []
[]

[BCs]
  # 远端液相保持名义成分
  [c_far]
    type = DirichletBC
    variable = c
    boundary = right
    value = 0.036
  []
[]

[Materials]
  [params]
    type = GenericConstantMaterial
    prop_names  = 'L          kappa_op  kappa_c   M'
    prop_values = '5.833e-4   3.6e-6    1.125e-11 2.8e-9'
  []

  # 【唯一的自由能】η 与 c 共用 ⇒ 变分耦合
  [F]
    type = DerivativeParsedMaterial
    property_name = F
    coupled_variables = 'eta c'
    constant_names = 'Wg dG k_c c0 A'
    constant_expressions = '7.2e6 -3.6e5 0.9 0.036 0.264'
    expression = 'Wg*eta^2*(1-eta)^2/4
                  + dG*eta^3*(10-15*eta+6*eta^2)
                  + k_c/2*(c-c0)^2
                  + A*c^2*eta^2'
    derivative_order = 2
  []
[]

[Postprocessors]
  # 固相长度 = ∫η dx（界面在 eta=0.5 处，故这是很好的前沿位置代理）
  [solid_len]
    type = ElementIntegralVariablePostprocessor
    variable = eta
    execute_on = 'initial timestep_end'
  []
  # 界面处液相浓度（c 沿程最大，因为界面处是 c0/k）
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'initial timestep_end'
  []
  # 【T3 的判据用这个】移动前沿下 c 必须保持非负：
  #     判据 min(c) >= -1e-10
  # 不加这条就只能靠肉眼看 Exodus，无法作为自动判据。
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'initial timestep_end'
  []
  # 固相深部浓度（左端固定，前沿右移后一直是固相）
  [c_solid]
    type = ElementalVariableValue
    variable = c
    elementid = 4
    execute_on = 'initial timestep_end'
  []
  # 远端液相浓度（应恒为 c0=0.036）
  [c_far]
    type = ElementalVariableValue
    variable = c
    elementid = 155
    execute_on = 'initial timestep_end'
  []
  # 守恒
  [total_c]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []
  # 越界检查
  [eta_max]
    type = NodalExtremeValue
    variable = eta
    value_type = max
    execute_on = 'timestep_end'
  []
  [eta_min]
    type = NodalExtremeValue
    variable = eta
    value_type = min
    execute_on = 'timestep_end'
  []
  [dt]
    type = TimestepSize
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  l_max_its = 50
  l_tol = 1e-8
  nl_max_its = 50
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-12
  # 前沿需走 ~5*delta_c = 10 µm；V=1.26e-3 => 7.9e-3 s
  end_time = 8.0e-3
  # 步长上限交给自适应步长自己找（分裂式 CH 的 4 阶项有稳定性限制，
  # 实测生产配置 dtmax=2e-6 恰好 = dx^4/(16*M*kappa_c)；本算例 dx 更细，
  # 先给宽松上限，让 IterationAdaptiveDT 自己收敛到稳定步长再读日志。
  dtmax = 2.0e-5
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.0e-6
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 8
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
  [exo]
    type = Exodus
    time_step_interval = 20
  []
[]
