# =============================================================================
# 阶段 2 生产算例（含晶界偏析）
# =============================================================================
#
# 与验证版 phase2_2d_seg.i 的差别：
#   - 晶粒数 60 → 100（粗化更快，事件来得早；数据量也更大）
#   - end_time 1500（约 5 小时）
#   - 多分散种子换回等尺寸随机（多分散那条路没走通，见下）
#
# 【为什么放弃多分散】
#   试过在常规晶粒旁 60 距离处塞小晶粒。结果尺寸分布只从 95 到 186
#   （自然涨落量级），没有形成真正的小晶粒——那些点被搭档的大晶粒吸收了。
#   改用"增加晶粒数"来加速粗化：理想晶粒长大 R² ∝ t，晶粒多 → R₀ 小 →
#   粗化时间 ∝ R₀² 更短。
#
# 【成本已实测】
#   每步约 20 秒，dt 稳定在 1.6 → 约 12.5 秒/时间单位
#   end_time=1500 → 约 5 小时
#   降迁移率、改耦合形式都不能放大 dt（瓶颈是 c-η 耦合，不是 c 自身的弛豫）
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 50
  ny = 50
  xmax = 1000
  ymax = 1000
  elem_type = QUAD4
  uniform_refine = 2          # → 200×200 = 40,000 单元，dx=5
  #   100 晶粒 → 平均晶粒尺寸 1000/10 = 100
  #   晶粒/晶界宽度 = 100/14 = 7.1×（比 60 晶粒时更宽松）
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
  [c]
    order = FIRST
    family = LAGRANGE
    [InitialCondition]
      type = RandomIC
      min = 0.3499
      max = 0.3501          # 近均匀初值，偏析由自由能驱动建立
    []
  []
  [w]
    order = FIRST
    family = LAGRANGE
  []
[]

[Kernels]
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
  [GB]
    type = GBEvolution
    T = 450
    wGB = 14
    GBmob0 = 2.5e-6
    Q = 0.23
    GBenergy = 0.708
  []

  # 自由能必须与 ACGBPoly 的二次耦合形式一致（改错会破坏变分自洽）
  [local_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7 gr8 gr9'
    material_property_names = 'mu gamma_asymm'
    constant_names = 'k c0 en_ratio A_scale'
    constant_expressions = '1.0 0.35 1.0 0.5'
    expression = 'k/2*(c-c0)^2
                  + A_scale*en_ratio*mu*gamma_asymm*c^2
                    *(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2
                     +gr5^2+gr6^2+gr7^2+gr8^2+gr9^2)'
  []

  [ch_params]
    type = GenericConstantMaterial
    prop_names = 'M kappa_c'
    prop_values = '1.0 1.0'
  []
[]

[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 100
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
  [dt]
    type = TimestepSize
  []
[]

# 求解设置：必须是 NEWTON + SMP full（PJFNK + hypre boomeramg 会线性发散）
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

  end_time = 1500

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.6
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
    time_step_interval = 5      # 每 5 步写一次，控制文件大小
    file_base = prod
    execute_on = 'initial timestep_end'
  []
[]
