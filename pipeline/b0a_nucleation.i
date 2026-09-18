# 【B0a 最小实验】澄清 reserve_op 的语义 —— 决定形核走哪条路
#
# 两次源码调研给出**冲突**的读法：
#   (i)  官方文档措辞：保留 op 是"暂存位"，晶粒在下一步被 remap 到普通 op 上
#   (ii) 源码引证（GrainTracker.C:1207,1239,1604-1605）：保留 op 上的晶粒
#        **永不被 remap**、**永远拿固定 ID**
#
# 两者对"路径 A 能否做多次形核"影响完全不同，必须实测。
#
# 判据（看 ElementExtremeValue 的 CSV）：
#   最终 max(gr3) ≈ 1  ->  语义 (ii)：核留在保留 op 上 -> 每个保留 op 是一个**永久槽位**
#   最终 max(gr3) → 0 且某个 gr0..gr2 增大 -> 语义 (i)：核被 remap 走了 -> 保留 op 是**可复用暂存位**
#
# 用 DiscreteNucleationFromFile 而非随机 inserter，保证可复现。

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 20
  ny = 20
  xmin = 0
  xmax = 20
  ymin = 0
  ymax = 20
  elem_type = QUAD4
[]

[GlobalParams]
  op_num = 4
  var_name_base = gr
[]

[Variables]
  [PolycrystalVariables]
  []
[]

[ICs]
  # 手工给两个晶粒：左半 gr0、右半 gr1，界面用 tanh 平滑（宽度 ~2，
  # 与 kappa/L 的量级匹配），避免尖锐不连续造成数值困难。
  # gr2 / gr3 保持初值 0（空闲）。
  [gr0_ic]
    type = FunctionIC
    variable = gr0
    function = '0.5*(1-tanh((x-10)/1.0))'
  []
  [gr1_ic]
    type = FunctionIC
    variable = gr1
    function = '0.5*(1+tanh((x-10)/1.0))'
  []
[]

[UserObjects]
  # 确定性形核：在 t=0.5 时刻于 (15, 15) 放一个核，hold_time 给足
  [inserter]
    type = DiscreteNucleationFromFile
    file = nuclei.csv
    hold_time = 1e9
    radius = 2
  []
  [map]
    type = DiscreteNucleationMap
    inserter = inserter
    int_width = 1
  []
  [grain_tracker]
    type = GrainTracker
    variable = 'gr0 gr1 gr2 gr3'
    # 【关键】保留最后 1 个 op（gr3）为形核专用
    reserve_op = 1
    remap_grains = true
    tracking_step = 0
    compute_var_to_feature_map = true
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  # 【为什么手写核而不用 GrainGrowth 动作】
  # 动作会为**全部** op（含保留 op gr3）生成 ACGrGrPoly + ACInterface，
  # 与形核力打架：实测 gr3 只长到 0.33、GrainTracker 始终不算第 3 个晶粒。
  # 手写可精确控制"哪些 op 有生长核"，这也是生产算例（splice_aniso.py）的做法。

  # --- 普通 op gr0..gr2：标准 Allen-Cahn（时间导数 + 体驱动力 + 界面能）---
  [gr0_dt]
    type = TimeDerivative
    variable = gr0
  []
  [gr0_poly]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr1 gr2'
    mob_name = L
  []
  [gr0_int]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
  []
  [gr1_dt]
    type = TimeDerivative
    variable = gr1
  []
  [gr1_poly]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0 gr2'
    mob_name = L
  []
  [gr1_int]
    type = ACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
  []
  [gr2_dt]
    type = TimeDerivative
    variable = gr2
  []
  [gr2_poly]
    type = ACGrGrPoly
    variable = gr2
    v = 'gr0 gr1'
    mob_name = L
  []
  [gr2_int]
    type = ACInterface
    variable = gr2
    mob_name = L
    kappa_name = kappa_op
  []

  # --- 保留 op gr3：只有形核力 + Reaction。
  #     Force 残差 -((v1-v0)M(r)+v0)*ψ 与 Reaction 残差 u*ψ 相加为零
  #     => u = M(r)(v1-v0)+v0，即把 gr3 钉在 map 的仿射变换上（核内 1、核外 0）。
  [gr3_force]
    type = DiscreteNucleationForce
    variable = gr3
    map = map
    no_nucleus_value = 0
    nucleus_value = 1
  []
  [gr3_react]
    type = Reaction
    variable = gr3
  []
[]

[Materials]
  # ACGrGrPoly 硬编码索取 mu 与 gamma_asymm（属性名不可改，见 moose-api-gotchas）。
  # 本实验只关心拓扑语义，数值取标准值即可。
  [const]
    type = GenericConstantMaterial
    prop_names = 'L kappa_op mu gamma_asymm'
    prop_values = '1.0 1.0 1.0 1.5'
  []
[]

[Postprocessors]
  # 每个 op 的最大值 —— 核是否留在 gr3 上，一眼可见
  [max_gr0]
    type = ElementExtremeValue
    variable = gr0
  []
  [max_gr1]
    type = ElementExtremeValue
    variable = gr1
  []
  [max_gr2]
    type = ElementExtremeValue
    variable = gr2
  []
  [max_gr3]
    type = ElementExtremeValue
    variable = gr3
  []
  # 各 op 的总量（看面积是否转移）
  [int_gr0]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
  []
  [int_gr1]
    type = ElementIntegralVariablePostprocessor
    variable = gr1
  []
  [int_gr2]
    type = ElementIntegralVariablePostprocessor
    variable = gr2
  []
  [int_gr3]
    type = ElementIntegralVariablePostprocessor
    variable = gr3
  []
  # GrainTracker 看到的晶粒总数
  [n_grains]
    type = FeatureFloodCount
    variable = 'gr0 gr1 gr2 gr3'
    compute_var_to_feature_map = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  nl_max_its = 20
  # 起始 dt 给小（见 ROADMAP §3.2 的坑）
  dt = 1e-3
  end_time = 2.0
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-3
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
    time_step_interval = 5
  []
[]
