# =============================================================================
# f_grain 正确性验证（Gate 0 步骤 4）
# =============================================================================
#
# 【理由】（2026-09-19 ④ 修复后更新）
#   `f_grain` 的表达式是从 MOOSE 源码 + 本算例的核结构反推的，反推错了
#   **不会报任何错**，只会静默给出错误的自由能。所以必须数值核对。
#
#   【2026-09-19 之前】f_grain = mu·[ Σ(η⁴/4 − η²/2) + γ Σ_{i<j} η²η² ]，
#      η 方程由一个 ACGrGrPoly 核给出，判据是 `ACGrGrPoly.C:61` 的逐字转录：
#          mu*(op³ − op + 2γ·op·Σ_{j≠i}op_j²)
#
#   【2026-09-19 ④ 修复后】η 方程由**两个**核相加给出：
#      ACGrGrPoly(mu = 常数 mu0)           →  mu0·(η³ − η + 2γηΣ)
#      AllenCahn(f_drive = (mu0−mu_T)/2·Ση²) → (mu0 − mu_T)·η
#      相加 / L  =  mu0·η³ − mu_T·η + 2·mu0·γ·η·Σ_{j≠i}η_j²
#   新的自由能（Landau 形式，见 stage1_meltpool_c.i 的长注释）：
#      f_grain = mu0·Σ(η⁴/4) − mu_T·Σ(η²)/2 + mu0·γ Σ_{i<j} η_i²η_j²
#   对其求 ∂/∂η₀ 正好等于上面两核之和 ⇒ 这正是本算例要核对的东西。
#
# 【判据】
#   数值微分      d(∫f_grain dV)/dηᵢ   （由 F_grain 在 ηᵢ 扰动 ±ε 下算出）
#   必须等于
#   解析积分      ∫ [ mu0·ηᵢ³ − mu_T·ηᵢ + 2·mu0·γ·ηᵢ·Σ_{j≠i}ηⱼ² ] dV
#
#   右边由 `dfdop_check*` 材料给出 —— 它是
#   「ACGrGrPoly.C:61 逐字转录 + f_drive 的 AllenCahn 导数」的**逐字组合**，
#   不是我重推的公式。
#
# 【设计要点】
#   * gr0/gr1/gr2 用 **AuxVariable**（带 initial_condition）—— 场不演化，
#     于是 ∫f_grain dV 是初值的纯函数，数值微分干净。
#     扰动通过 CLI 覆盖 `AuxVariables/gr0/initial_condition=...` 施加。
#   * **T 取 1870 K（不是 1000 K）**：让 mu_T = 0.25074·mu0 ≠ mu0，
#     这样"新形式"与"旧形式"的判据**不相等**，本算例才有鉴别力。
#     （T ≤ ~1500 K 时 tanh→−1 ⇒ mu_T = mu0，新旧两式恒等，验了等于没验。）
#   * 另加一个平凡的非线性变量 u（Diffusion + DirichletBC），只是为了让求解器有活干。
#   * 域取 [0,1]²，均匀场 ⇒ 体积（面积）= 1，后处理器数值 = 被积函数值。
#
# 【运行方式】
#   对 η₀ ∈ {0.6−2ε, 0.6−ε, 0.6+ε, 0.6+2ε} 各跑一次，取 F_grain，
#   用四点中心差分求 dF/dη₀，与 M0 比较。见 tests/run_verify_f_grain.py。
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 2
  ny = 2
  xmin = 0.0
  xmax = 1.0
  ymin = 0.0
  ymax = 1.0
  elem_type = QUAD4
[]

[AuxVariables]
  # 序参量：用 AuxVariable 使场不演化（本算例只验材料属性，不解物理）
  [gr0]
    initial_condition = 0.6
  []
  [gr1]
    initial_condition = 0.35
  []
  [gr2]
    initial_condition = 0.15
  []
  [T]
    # 【④ 修复】取 1870 K 而**不是** 1000 K：让 mu_T = 0.25074·mu0 ≠ mu0，
    #   这样"新形式"与"旧形式"的判据不相等，本算例才有鉴别力。
    #   tanh((1000-1903)/60) ≈ −1 ⇒ mu_T = mu0 ⇒ 新旧两式恒等，验了等于没验。
    initial_condition = 1870
  []
[]

[Variables]
  # 平凡变量，仅为让求解器有自由度
  [u]
  []
[]

[Kernels]
  [d]
    type = Diffusion
    variable = u
  []
[]

[BCs]
  [l]
    type = DirichletBC
    variable = u
    boundary = left
    value = 0.3
  []
  [r]
    type = DirichletBC
    variable = u
    boundary = right
    value = 0.7
  []
[]

[Materials]
  # 与生产输入 stage1_meltpool_c.i 的 [consts] 一致
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'gamma_asymm'
    prop_values = '1.5'
  []

  # 与生产输入的 [mu_barrier_const] 逐字一致（ACGrGrPoly 消费的常数势垒）
  [mu_barrier_const]
    type = GenericConstantMaterial
    prop_names  = 'mu'
    prop_values = '9.0e5'
  []

  # 与生产输入的 [barrier_muT] 逐字一致（熔化开关）
  [barrier_muT]
    type = DerivativeParsedMaterial
    property_name = mu_T
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
  []

  # ---- 被验证的对象：④ 修复后的 Landau 自由能 ----
  # ⚠ 与生产输入 stage1_meltpool_c.i 的 [f_grain] 是**同一形式的截断**
  #   （这里 3 个序参量、3 个交叉项；生产 8 个序参量、28 个交叉项）。
  #   改生产那个表达式时，这里必须同步改 —— 否则验证通过也说明不了生产。
  [f_grain]
    type = DerivativeParsedMaterial
    property_name = f_grain
    coupled_variables = 'gr0 gr1 gr2'
    material_property_names = 'mu mu_T gamma_asymm'
    expression = 'mu*(gr0^4/4+gr1^4/4+gr2^4/4
                   +gamma_asymm*(gr0^2*gr1^2+gr0^2*gr2^2+gr1^2*gr2^2))
                  - mu_T/2*(gr0^2+gr1^2+gr2^2)'
    derivative_order = 1
  []

  # ---- 判据：η 方程里两个核的残差之和（都是逐字转录，不是重推）----
  #   ACGrGrPoly.C:61  →  mu*(op³ − op + 2γ·op·Σ_{j≠i}op_j²)
  #   AllenCahn(f_drive) → ∂f_drive/∂op = (mu − mu_T)·op
  #                        其中 f_drive = (mu − mu_T)/2·Σ η²
  #   相加 / L = mu·op³ − mu_T·op + 2·mu·γ·op·Σ_{j≠i}op_j²
  [dfdop_check0]
    type = ParsedMaterial
    property_name = dfdop0
    coupled_variables = 'gr0 gr1 gr2'
    material_property_names = 'mu mu_T gamma_asymm'
    expression = 'mu*(gr0^3-gr0+2*gamma_asymm*gr0*(gr1^2+gr2^2)) + (mu-mu_T)*gr0'
  []
  [dfdop_check1]
    type = ParsedMaterial
    property_name = dfdop1
    coupled_variables = 'gr0 gr1 gr2'
    material_property_names = 'mu mu_T gamma_asymm'
    expression = 'mu*(gr1^3-gr1+2*gamma_asymm*gr1*(gr0^2+gr2^2)) + (mu-mu_T)*gr1'
  []
  [dfdop_check2]
    type = ParsedMaterial
    property_name = dfdop2
    coupled_variables = 'gr0 gr1 gr2'
    material_property_names = 'mu mu_T gamma_asymm'
    expression = 'mu*(gr2^3-gr2+2*gamma_asymm*gr2*(gr0^2+gr1^2)) + (mu-mu_T)*gr2'
  []
[]

[Postprocessors]
  [vol]
    type = VolumePostprocessor
    execute_on = timestep_end
  []
  # 被验证的自由能积分
  [F_grain]
    type = ElementIntegralMaterialProperty
    mat_prop = f_grain
    execute_on = timestep_end
  []
  # 判据：解析导数的积分（应等于 dF_grain/dηᵢ）
  [M0]
    type = ElementIntegralMaterialProperty
    mat_prop = dfdop0
    execute_on = timestep_end
  []
  [M1]
    type = ElementIntegralMaterialProperty
    mat_prop = dfdop1
    execute_on = timestep_end
  []
  [M2]
    type = ElementIntegralMaterialProperty
    mat_prop = dfdop2
    execute_on = timestep_end
  []
  # 材料属性本身（供人读核对，不做判据）
  [mu_val]
    type = ElementAverageValue
    variable = T
    execute_on = timestep_end
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  dt = 1
  end_time = 1
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
