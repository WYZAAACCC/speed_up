# =============================================================================
# 组装版：共形面块 + 体相↔面通量耦合（3D Gibbs 面，Γ 与 c 真正耦合）
# =============================================================================
# 物理
#   Γ = A_s·c_GB                     （McLean 等温线，Henry 极限；A_s = Γ_0·K(T)）
#   面上:  dΓ/dt = k_att·(A_s·c − Γ)     ⇒  用 Gam ≡ Γ/A_s (无量纲等效浓度)
#          dGam/dt = k_att·(c − Gam)
#   体相:  GB 面上溶质被抽走，通量 = −(A_s·k_att/ρ_mol)·(c − Gam)   [无量纲/面积/时间]
#
# ★ 关键技巧：InterfaceKernel 只有**一个**系数，而物理上两侧差 A_s/ρ_mol。
#   ⇒ 把面方程**整体乘 (A_s/ρ_mol)**，两侧系数就统一成 K = A_s·k_att/ρ_mol
#     面方程的 dGam/dt 项用本 app 自建的 ScaledTimeDerivative（scale = A_s/ρ_mol）
#
# 解析预期（由总量守恒解出 c_f）
#   ρ_mol·c_f·V + A_s·c_f·A = ρ_mol·c0·V
#   ⇒ c_f = @CF@  （体相贫化 @DEP@%）
#   ⇒ 平衡时 Gam → c_f ，且 ρ_mol·c·V + A_s·Gam·A 守恒
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
  # ★ 显式造出「体块 0 ↔ 低维块 2」的界面 sideset —— InterfaceKernel 要的是这个
  [gb_ld_ss]
    type = SideSetsBetweenSubdomainsGenerator
    input = gb_block
    primary_block = 0
    paired_block = 2
    new_boundary = gb_ld
  []
  displacements = 'disp_x disp_y disp_z'
[]

[Functions]
  [zero_fn]
    type = ParsedFunction
    expression = '0'
  []
  # y 向均匀应变 eps(t) = EPSK*t ⇒ 晶界面（x=const 平面）面积按 (1+eps) 变化
  [strain_fn]
    type = ParsedFunction
    expression = '@EPSK@ * t * y'
  []
[]
[AuxVariables]
  [disp_x]
  []
  [disp_y]
  []
  [disp_z]
  []
[]
[AuxKernels]
  [disp_x_k]
    type = FunctionAux
    variable = disp_x
    function = zero_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
  [disp_y_k]
    type = FunctionAux
    variable = disp_y
    function = strain_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
  [disp_z_k]
    type = FunctionAux
    variable = disp_z
    function = zero_fn
    use_displaced_mesh = false
    execute_on = 'initial timestep_end'
  []
[]
[Variables]
  [c]
    block = '0 1'
    initial_condition = @C0@
  []
  [Gam]
    block = 2
    initial_condition = 0
  []
[]

[Kernels]
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
  # ★ 动态项：材料以速度 v 流过晶界（= 晶界在材料里以 v 迁移，取晶界参考系）
  #   对常速度场，ConservativeAdvection 给的 div(v*c) 等于 v·grad(c)
  [c_adv]
    type = ConstAdvection
    variable = c
    vel_name = vel
    block = '0 1'
  []
  # (A_s/ρ_mol)·dGam/dt
  [gam_dt]
    type = ScaledTimeDerivative
    variable = Gam
    block = 2
    scale = AsRho
    use_displaced_mesh = true
  []
[]

[Constraints]
  [gb_exchange]
    type = GBFluxExchange
    variable = Gam
    secondary_variable = c
    primary_variable = c
    secondary_boundary = gb
    primary_boundary = gb
    secondary_subdomain = gbb
    primary_subdomain = gbb
    kex = kex
  []
[]

[Materials]
  [D_bulk]
    type = GenericConstantMaterial
    prop_names = 'D_bulk'
    prop_values = '4e-13'
  []
  [vel]
    type = GenericConstantRealVectorValue
    vector_name = vel
    vector_values = '@V@ 0 0'
  []
  # A_s/ρ_mol  [m]
  [AsRho]
    type = GenericConstantMaterial
    prop_names = 'AsRho'
    prop_values = '@ASRHO@'
  []
  # K = A_s·k_att/ρ_mol
  [kex]
    type = GenericConstantMaterial
    prop_names = 'kex'
    prop_values = '@KEX@'
  []
[]

[BCs]
  # 入口补流：材料从 x=0 流入，成分 c0
  [inflow]
    type = DirichletBC
    variable = c
    boundary = left
    value = @C0@
  []
[]

[Postprocessors]
  [flux_in]
    type = SideFluxIntegral
    variable = c
    boundary = left
    diffusivity = D_bulk
  []
  [flux_out]
    type = SideFluxIntegral
    variable = c
    boundary = right
    diffusivity = D_bulk
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
  [gam_int]
    type = ElementIntegralVariablePostprocessor
    variable = Gam
    block = 2
    execute_on = 'initial timestep_end'
  []
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    block = '0 1'
    execute_on = 'timestep_end'
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    block = '0 1'
    execute_on = 'timestep_end'
  []
  [c_int]
    type = ElementIntegralVariablePostprocessor
    variable = c
    block = '0 1'
    execute_on = 'initial timestep_end'
  []
  # 总溶质（守恒量）：ρ_mol·∫c dV + A_s·∫Gam dA
  [total_solute]
    type = ParsedPostprocessor
    expression = '@RHOMOL@*c_int + @AS@*gam_int'
    pp_names = 'c_int gam_int'
    execute_on = 'initial timestep_end'
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-24
  dt = @DT@
  end_time = @TEND@
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = @DT@
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]