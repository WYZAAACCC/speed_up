# =============================================================================
# 最小判据实验：**竞争生长机制到底有没有在起作用**
# =============================================================================
#
# 【为什么这样设计】2b 是"迁移率各向异性"。平直晶界在静态下没有驱动力
# （无曲率、无储能差），所以**单靠 2b 不会让晶界移动**。真实 LPBF 的竞争生长
# 来自"晶粒向液相生长、热梯度提供驱动力"，迁移率各向异性只是偏置谁长得快。
# 因此本实验必须有**固液界面**。
#
# 设置：
#   域 40um x 40um，网格 1um（与真实算例同分辨率，界面宽 4um = 4 个单元）
#   两个晶粒：x<20um 是 gr0（theta=0，易生长轴沿 y = 与梯度对齐），
#             x>20um 是 gr1（theta=45，完全不对齐）
#   固液界面在 y0 处，上方是液相；温度场随 y 升高、随时间下降 -> 界面向上推进
#   梯度沿 +y -> phi=90 度：
#       gp = (gx^2-gy^2)/(G+eps) = -1 ,  gq = 2*gx*gy/(G+eps) = 0
#       align4 = [gr0^2*(cos0*gp+sin0*gq)^2 + gr1^2*(cos90*gp+sin90*gq)^2]/(sum gr^2+1e-3)
#              = [gr0^2*1 + gr1^2*0]/(...)   ->  gr0 里 =1（完全对齐），gr1 里 =0（完全不对齐）
#       L2b = 1 + A*(2*align4-1)  ->  gr0: 1+A , gr1: 1-A
#   A_ani = 0.7 -> gr0 的迁移率是 gr1 的 1.7/0.3 = 5.67 倍
#
# 判据：
#   * **收敛性**：Newton 应二次收敛 + ||J-Jfd||/||J|| 应达 ~1e-8（AD 精确雅可比）
#   * **正确性**：gr0（对齐晶粒）在凝固区中的面积分数应**单调上升超过 50%**
#   * **对照**：A_ani=0 时应无择优（面积分数基本不变）
#
# 用 AD 核 + AD 派生材料（雅可比精确），以同时验证收敛性。
# 温度用 AuxVariable 解析给定（不解热方程）-> 算例很小很快。
# =============================================================================

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 40
  ny = 40
  xmin = 0
  xmax = 4e-5
  ymin = 0
  ymax = 4e-5
[]

# 不用 [GlobalParams] op_num/var_name_base —— 本算例显式声明 gr0/gr1 两个变量，
# 不走 PolycrystalVariables 动作，留着会报 "unused parameter"。

[Variables]
  [gr0]
    order = FIRST
    family = LAGRANGE
  []
  [gr1]
    order = FIRST
    family = LAGRANGE
  []
[]

[AuxVariables]
  [T]
    order = FIRST
    family = LAGRANGE
  []
[]

[Functions]
  # 温度：底部冷、顶部热；整体随时间下降 -> 固液界面（T=1903）向上推进
  [temp_fn]
    type = ParsedFunction
    expression = '1830 + 300*y/4e-5 - 220*t/6e-4'
  []
  # 固相掩膜：y < y0(t) 处为 1。y0 由 T=1903 解出：
  #   1903 = 1830 + 300*y0/4e-5 - 220*t/6e-4  ->  y0 = 4e-5*(73 + 220*t/6e-4)/300
  # 用 tanh 平滑过渡，宽度取界面宽 4um
  [solid0_fn]
    type = ParsedFunction
    expression = '0.5*(1+tanh((2e-5-x)/1e-6)) * 0.5*(1+tanh((4e-5*(73+220*t/6e-4)/300 - y)/1e-6))'
  []
  [solid1_fn]
    type = ParsedFunction
    expression = '0.5*(1+tanh((x-2e-5)/1e-6)) * 0.5*(1+tanh((4e-5*(73+220*t/6e-4)/300 - y)/1e-6))'
  []
[]

[ICs]
  [ic0]
    type = FunctionIC
    variable = gr0
    function = solid0_fn
  []
  [ic1]
    type = FunctionIC
    variable = gr1
    function = solid1_fn
  []
[]

[AuxKernels]
  [T_aux]
    type = FunctionAux
    variable = T
    function = temp_fn
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  # AD 核：雅可比精确（ACGrGrPoly 的离对角雅可比丢了 dL/deta_j，AD 版不会）
  [gr0_dt]
    type = ADTimeDerivative
    variable = gr0
  []
  [gr0_poly]
    type = ADGrainGrowth
    variable = gr0
    v = 'gr1'
    mob_name = L
  []
  [gr0_int]
    type = ADACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr1'
  []
  [gr1_dt]
    type = ADTimeDerivative
    variable = gr1
  []
  [gr1_poly]
    type = ADGrainGrowth
    variable = gr1
    v = 'gr0'
    mob_name = L
  []
  [gr1_int]
    type = ADACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr0'
  []
[]

[Materials]
  [consts]
    type = ADGenericConstantMaterial
    prop_names = 'kappa_op gamma_asymm'
    prop_values = '1.8e-6 1.5'
  []
  # 熔化开关（与真实算例同形式同参数）
  [barrier_mu]
    type = ADDerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
  []
  # 对齐度（内联，不用 material_property_names）：
  #   梯度沿 +y -> gdir_p = -1, gdir_q = 0
  #   align4 = [gr0^2*(cos0*gdir_p+sin0*gdir_q)^2 + gr1^2*(cos90*gdir_p+sin90*gdir_q)^2]/(sum+1e-3)
  #          = [gr0^2*1 + gr1^2*0]/(gr0^2+gr1^2+1e-3)
  #   -> gr0 里 = 1（与梯度完全对齐）, gr1 里 = 0（完全不对齐）
  #
  # 【为什么不拆成 gdir_p/gdir_q 两个材料】那需要 AD 材料消费
  # material_property_names，而这个机制我**没有验证过**（非 AD 下验证过，
  # AD 下没有）。内联后只剩显式表达式，零机制风险。
  [L_aniso]
    type = ADDerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T gr0 gr1'
    expression = '((4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-6)*(1+0.7*(2*(gr0^2/(gr0^2+gr1^2+1e-3))-1))'
    derivative_order = 1
  []
  # 仅用于诊断输出（align4 不在 L 里单独出现了，这里重算一份给 postprocessor）
  [align4_prop]
    type = ADParsedMaterial
    property_name = align4
    coupled_variables = 'gr0 gr1'
    expression = 'gr0^2/(gr0^2+gr1^2+1e-3)'
  []
[]

[Postprocessors]
  # gr0 在**已凝固区域**中的面积分数 —— 竞争生长的直接判据
  [gr0_total]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
  []
  [gr1_total]
    type = ElementIntegralVariablePostprocessor
    variable = gr1
  []
  # 注意两点（都踩过）：
  #   1. align4 是**材料属性**不是变量 -> 不能用 ElementAverageValue
  #      （报 "coupled variable 'align4' was not found"）
  #   2. ADElementExtremeMaterialProperty 只支持 max/min，**没有 mean**
  #      （报 'Invalid option "mean"'）
  [align_max]
    type = ADElementExtremeMaterialProperty
    mat_prop = align4
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [mu_min]
    type = ADElementExtremeMaterialProperty
    mat_prop = mu
    value_type = min
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  dt = 2e-6
  end_time = 6e-4
  dtmax = 4e-6
  nl_max_its = 30
  l_max_its = 300
  l_tol = 1e-8
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-9
  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'
  petsc_options_value = 'asm 31 preonly ilu 1'
[]

[Outputs]
  csv = true
  print_linear_residuals = true
  [exo]
    type = Exodus
    time_step_interval = 20
    file_base = cg
  []
[]
