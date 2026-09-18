# =============================================================================
# 阶段一 · D 版 = C 版（柱状基体 + 溶质，已验证） + 第二档（2a + 2b）
# =============================================================================
#
# D 版相对 C 版**只改晶界性质，不改任何其他物理**：
#
#   [consts]     kappa_op=1.8e-6, gamma_asymm=1.5   （常数）
#   [L_mobility] L = 4/3*M0*exp(-Q/kbT)/wGB         （各向同性 Arrhenius）
#       ↓ 被替换为
#   [kappa_aniso] [gamma_aniso] [L_aniso]           （2a + 2b，见 aniso_block.i）
#
#   barrier_mu（熔化开关）、溶质系统、温度场、网格、求解器  —— **全部未动**
#
# 【2a】取向差依赖的晶界能/迁移率
#   严格复刻 GBAnisotropy 的 Moelans Algorithm 1（不用该材料的原因见
#   gen_aniso.py 头注释：它会声明 `mu`，与熔化开关抢同名属性）。
#   各向同性极限下 kappa_op/gamma_asymm/L **都精确退化为 C 版的值**
#   （kappa 偏差 3.17e-05，来自教科书圆整值 0.75 vs 不动点精确解 0.74997626）。
#
# 【2b】热梯度驱动的晶粒选择
#   对齐因子 (1 + A*(2*align4 - 1))，align4 = cos^2(2(phi-theta)) 四重对称。
#   热梯度取实际温度场的**解析导数**，不是几何近似。
#
# 【本版新增输出】orient_cos / orient_sin / grad_align（逐单元定值）
#   extract.py 靠前两个逐晶粒反解出晶粒取向 theta；
#   grad_align 用于与 extract.py 独立算出的对齐度交叉校验。
#
# 【已知简化，非 bug】
#   * 无形核核 -> 无等轴晶形核（真实 LPBF 熔池顶部有）
#   * A_ani = 0.7 是唯象占位，需用 LPBF 实测织构标定
#   * Q 的取向差依赖未建模（缺少文献依据），仅 sigma 与 M 有取向差依赖
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
    expression = '353 + 28/(2*pi*20*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-0.6*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+x+1.2e-4-0.6*t)/(2*6e-06))'
  []
  [gradTx_fn]
    type = ParsedFunction
    expression = '(0.2228169203/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t)))*(-(x+1.2e-4-0.6*t)/(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t))/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))'
  []
  [gradTy_fn]
    type = ParsedFunction
    expression = '(0.2228169203/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t)))*(-y/(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))-50000*y/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))'
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
  [c_init]
    type = ConstantIC
    variable = c
    value = 0.35
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
  [grad_Tx]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_Ty]
    order = CONSTANT
    family = MONOMIAL
  []
  [orient_cos]
    order = CONSTANT
    family = MONOMIAL
  []
  [orient_sin]
    order = CONSTANT
    family = MONOMIAL
  []
  [grad_align]
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
  [grad_Tx]
    type = FunctionAux
    variable = grad_Tx
    function = gradTx_fn
    execute_on = 'initial timestep_end'
  []
  [grad_Ty]
    type = FunctionAux
    variable = grad_Ty
    function = gradTy_fn
    execute_on = 'initial timestep_end'
  []
  # 局部取向（eta^2 加权）—— 只依赖 eta，故 ParsedAux 可用。
  # extract.py 逐晶粒反解出 theta，这个量对 remap 免疫。
  [orient_cos]
    type = ParsedAux
    variable = orient_cos
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = '(gr0^2*1 + gr1^2*0.966600102 + gr2^2*0.8686315144 + gr3^2*0.822640518 + gr4^2*0.6494480483 + gr5^2*0.4328725815 + gr6^2*0.3534748438 + gr7^2*0.1019244558)/(gr0^2 + gr1^2 + gr2^2 + gr3^2 + gr4^2 + gr5^2 + gr6^2 + gr7^2+1e-20)'
    execute_on = 'initial timestep_end'
  []
  [orient_sin]
    type = ParsedAux
    variable = orient_sin
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = '(gr0^2*0 + gr1^2*0.2562893731 + gr2^2*0.4954586684 + gr3^2*0.5685618507 + gr4^2*0.7604059656 + gr5^2*0.9014551171 + gr6^2*0.9354440308 + gr7^2*0.9947921418)/(gr0^2 + gr1^2 + gr2^2 + gr3^2 + gr4^2 + gr5^2 + gr6^2 + gr7^2+1e-20)'
    execute_on = 'initial timestep_end'
  []
  # 对齐度从材料里取出，保证与 L 里用的是同一个数（不是重算一遍）
  [grad_align]
    type = MaterialRealAux
    variable = grad_align
    property = align4
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
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
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
  # --- 2a: 晶界能 kappa_op（逐对取向差加权）---
  # 各向同性极限 = 1.8e-6，与引入 2a 之前逐位相同
  [kappa_aniso]
    type = DerivativeParsedMaterial
    property_name = kappa_op
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = '(1.799852707e-06*(gr0^2+1e-7)*(gr1^2+1e-7) + 1.799943021e-06*(gr0^2+1e-7)*(gr2^2+1e-7) + 1.799943021e-06*(gr0^2+1e-7)*(gr3^2+1e-7) + 1.799943021e-06*(gr0^2+1e-7)*(gr4^2+1e-7) + 1.799943021e-06*(gr0^2+1e-7)*(gr5^2+1e-7) + 1.799943021e-06*(gr0^2+1e-7)*(gr6^2+1e-7) + 1.359569168e-06*(gr0^2+1e-7)*(gr7^2+1e-7) + 1.799852707e-06*(gr1^2+1e-7)*(gr2^2+1e-7) + 1.799943021e-06*(gr1^2+1e-7)*(gr3^2+1e-7) + 1.799943021e-06*(gr1^2+1e-7)*(gr4^2+1e-7) + 1.799943021e-06*(gr1^2+1e-7)*(gr5^2+1e-7) + 1.799943021e-06*(gr1^2+1e-7)*(gr6^2+1e-7) + 1.799943021e-06*(gr1^2+1e-7)*(gr7^2+1e-7) + 1.247493933e-06*(gr2^2+1e-7)*(gr3^2+1e-7) + 1.799943021e-06*(gr2^2+1e-7)*(gr4^2+1e-7) + 1.799943021e-06*(gr2^2+1e-7)*(gr5^2+1e-7) + 1.799943021e-06*(gr2^2+1e-7)*(gr6^2+1e-7) + 1.799943021e-06*(gr2^2+1e-7)*(gr7^2+1e-7) + 1.799852707e-06*(gr3^2+1e-7)*(gr4^2+1e-7) + 1.799943021e-06*(gr3^2+1e-7)*(gr5^2+1e-7) + 1.799943021e-06*(gr3^2+1e-7)*(gr6^2+1e-7) + 1.799943021e-06*(gr3^2+1e-7)*(gr7^2+1e-7) + 1.799852707e-06*(gr4^2+1e-7)*(gr5^2+1e-7) + 1.799943021e-06*(gr4^2+1e-7)*(gr6^2+1e-7) + 1.799943021e-06*(gr4^2+1e-7)*(gr7^2+1e-7) + 1.247493933e-06*(gr5^2+1e-7)*(gr6^2+1e-7) + 1.799943021e-06*(gr5^2+1e-7)*(gr7^2+1e-7) + 1.799852707e-06*(gr6^2+1e-7)*(gr7^2+1e-7))/((gr0^2+1e-7)*(gr1^2+1e-7) + (gr0^2+1e-7)*(gr2^2+1e-7) + (gr0^2+1e-7)*(gr3^2+1e-7) + (gr0^2+1e-7)*(gr4^2+1e-7) + (gr0^2+1e-7)*(gr5^2+1e-7) + (gr0^2+1e-7)*(gr6^2+1e-7) + (gr0^2+1e-7)*(gr7^2+1e-7) + (gr1^2+1e-7)*(gr2^2+1e-7) + (gr1^2+1e-7)*(gr3^2+1e-7) + (gr1^2+1e-7)*(gr4^2+1e-7) + (gr1^2+1e-7)*(gr5^2+1e-7) + (gr1^2+1e-7)*(gr6^2+1e-7) + (gr1^2+1e-7)*(gr7^2+1e-7) + (gr2^2+1e-7)*(gr3^2+1e-7) + (gr2^2+1e-7)*(gr4^2+1e-7) + (gr2^2+1e-7)*(gr5^2+1e-7) + (gr2^2+1e-7)*(gr6^2+1e-7) + (gr2^2+1e-7)*(gr7^2+1e-7) + (gr3^2+1e-7)*(gr4^2+1e-7) + (gr3^2+1e-7)*(gr5^2+1e-7) + (gr3^2+1e-7)*(gr6^2+1e-7) + (gr3^2+1e-7)*(gr7^2+1e-7) + (gr4^2+1e-7)*(gr5^2+1e-7) + (gr4^2+1e-7)*(gr6^2+1e-7) + (gr4^2+1e-7)*(gr7^2+1e-7) + (gr5^2+1e-7)*(gr6^2+1e-7) + (gr5^2+1e-7)*(gr7^2+1e-7) + (gr6^2+1e-7)*(gr7^2+1e-7))'
    derivative_order = 1
  []
  # --- 2a: gamma_asymm（逐对加权）---
  # 各向同性极限 = 1.5
  [gamma_aniso]
    type = DerivativeParsedMaterial
    property_name = gamma_asymm
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = '(1.499817977*(gr0^2+1e-7)*(gr1^2+1e-7) + 1.499918283*(gr0^2+1e-7)*(gr2^2+1e-7) + 1.499918283*(gr0^2+1e-7)*(gr3^2+1e-7) + 1.499918283*(gr0^2+1e-7)*(gr4^2+1e-7) + 1.499918283*(gr0^2+1e-7)*(gr5^2+1e-7) + 1.499918283*(gr0^2+1e-7)*(gr6^2+1e-7) + 1.104480005*(gr0^2+1e-7)*(gr7^2+1e-7) + 1.499817977*(gr1^2+1e-7)*(gr2^2+1e-7) + 1.499918283*(gr1^2+1e-7)*(gr3^2+1e-7) + 1.499918283*(gr1^2+1e-7)*(gr4^2+1e-7) + 1.499918283*(gr1^2+1e-7)*(gr5^2+1e-7) + 1.499918283*(gr1^2+1e-7)*(gr6^2+1e-7) + 1.499918283*(gr1^2+1e-7)*(gr7^2+1e-7) + 1.02744334*(gr2^2+1e-7)*(gr3^2+1e-7) + 1.499918283*(gr2^2+1e-7)*(gr4^2+1e-7) + 1.499918283*(gr2^2+1e-7)*(gr5^2+1e-7) + 1.499918283*(gr2^2+1e-7)*(gr6^2+1e-7) + 1.499918283*(gr2^2+1e-7)*(gr7^2+1e-7) + 1.499817977*(gr3^2+1e-7)*(gr4^2+1e-7) + 1.499918283*(gr3^2+1e-7)*(gr5^2+1e-7) + 1.499918283*(gr3^2+1e-7)*(gr6^2+1e-7) + 1.499918283*(gr3^2+1e-7)*(gr7^2+1e-7) + 1.499817977*(gr4^2+1e-7)*(gr5^2+1e-7) + 1.499918283*(gr4^2+1e-7)*(gr6^2+1e-7) + 1.499918283*(gr4^2+1e-7)*(gr7^2+1e-7) + 1.02744334*(gr5^2+1e-7)*(gr6^2+1e-7) + 1.499918283*(gr5^2+1e-7)*(gr7^2+1e-7) + 1.499817977*(gr6^2+1e-7)*(gr7^2+1e-7))/((gr0^2+1e-7)*(gr1^2+1e-7) + (gr0^2+1e-7)*(gr2^2+1e-7) + (gr0^2+1e-7)*(gr3^2+1e-7) + (gr0^2+1e-7)*(gr4^2+1e-7) + (gr0^2+1e-7)*(gr5^2+1e-7) + (gr0^2+1e-7)*(gr6^2+1e-7) + (gr0^2+1e-7)*(gr7^2+1e-7) + (gr1^2+1e-7)*(gr2^2+1e-7) + (gr1^2+1e-7)*(gr3^2+1e-7) + (gr1^2+1e-7)*(gr4^2+1e-7) + (gr1^2+1e-7)*(gr5^2+1e-7) + (gr1^2+1e-7)*(gr6^2+1e-7) + (gr1^2+1e-7)*(gr7^2+1e-7) + (gr2^2+1e-7)*(gr3^2+1e-7) + (gr2^2+1e-7)*(gr4^2+1e-7) + (gr2^2+1e-7)*(gr5^2+1e-7) + (gr2^2+1e-7)*(gr6^2+1e-7) + (gr2^2+1e-7)*(gr7^2+1e-7) + (gr3^2+1e-7)*(gr4^2+1e-7) + (gr3^2+1e-7)*(gr5^2+1e-7) + (gr3^2+1e-7)*(gr6^2+1e-7) + (gr3^2+1e-7)*(gr7^2+1e-7) + (gr4^2+1e-7)*(gr5^2+1e-7) + (gr4^2+1e-7)*(gr6^2+1e-7) + (gr4^2+1e-7)*(gr7^2+1e-7) + (gr5^2+1e-7)*(gr6^2+1e-7) + (gr5^2+1e-7)*(gr7^2+1e-7) + (gr6^2+1e-7)*(gr7^2+1e-7))'
    derivative_order = 1
  []
  # --- 2b 第一层：取向与热梯度的四重对齐度 ---
  # align4 = cos^2(2(phi-theta)) in [0,1]
  # 用四重而非二重：beta-Ti 的 <100> 在 2D 是四重对称，
  # theta 与 theta+90 是同一个取向，二重形式会把它们判成不同 —— 错。
  [align4_prop]
    type = DerivativeParsedMaterial
    property_name = align4
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7 grad_Tx grad_Ty'
    expression = '((2*(((gr0^2*1 + gr1^2*0.966600102 + gr2^2*0.8686315144 + gr3^2*0.822640518 + gr4^2*0.6494480483 + gr5^2*0.4328725815 + gr6^2*0.3534748438 + gr7^2*0.1019244558)*grad_Tx+(gr0^2*0 + gr1^2*0.2562893731 + gr2^2*0.4954586684 + gr3^2*0.5685618507 + gr4^2*0.7604059656 + gr5^2*0.9014551171 + gr6^2*0.9354440308 + gr7^2*0.9947921418)*grad_Ty)^2/(((gr0^2*1 + gr1^2*0.966600102 + gr2^2*0.8686315144 + gr3^2*0.822640518 + gr4^2*0.6494480483 + gr5^2*0.4328725815 + gr6^2*0.3534748438 + gr7^2*0.1019244558)^2+(gr0^2*0 + gr1^2*0.2562893731 + gr2^2*0.4954586684 + gr3^2*0.5685618507 + gr4^2*0.7604059656 + gr5^2*0.9014551171 + gr6^2*0.9354440308 + gr7^2*0.9947921418)^2+1e-8)*(grad_Tx^2+grad_Ty^2)))-1)^2)'
    derivative_order = 2
  []
  # --- 2b 第二层：各向异性因子 in [1-A, 1+A] ---
  [L2b]
    type = DerivativeParsedMaterial
    property_name = L2b
    material_property_names = 'align4'
    expression = '1+0.7*(2*align4-1)'
    derivative_order = 2
  []
  # --- 2a: 迁移率（不含量纲外的因子，各向同性极限 = 4/3*M0*exp(-Q/kbT)/wGB）---
  [L2a]
    type = DerivativeParsedMaterial
    property_name = L2a
    coupled_variables = 'T gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = '(0.99*(gr0^2+1e-7)*(gr1^2+1e-7) + 1*(gr0^2+1e-7)*(gr2^2+1e-7) + 1*(gr0^2+1e-7)*(gr3^2+1e-7) + 1*(gr0^2+1e-7)*(gr4^2+1e-7) + 1*(gr0^2+1e-7)*(gr5^2+1e-7) + 1*(gr0^2+1e-7)*(gr6^2+1e-7) + 0.39*(gr0^2+1e-7)*(gr7^2+1e-7) + 0.99*(gr1^2+1e-7)*(gr2^2+1e-7) + 1*(gr1^2+1e-7)*(gr3^2+1e-7) + 1*(gr1^2+1e-7)*(gr4^2+1e-7) + 1*(gr1^2+1e-7)*(gr5^2+1e-7) + 1*(gr1^2+1e-7)*(gr6^2+1e-7) + 1*(gr1^2+1e-7)*(gr7^2+1e-7) + 0.33*(gr2^2+1e-7)*(gr3^2+1e-7) + 1*(gr2^2+1e-7)*(gr4^2+1e-7) + 1*(gr2^2+1e-7)*(gr5^2+1e-7) + 1*(gr2^2+1e-7)*(gr6^2+1e-7) + 1*(gr2^2+1e-7)*(gr7^2+1e-7) + 0.99*(gr3^2+1e-7)*(gr4^2+1e-7) + 1*(gr3^2+1e-7)*(gr5^2+1e-7) + 1*(gr3^2+1e-7)*(gr6^2+1e-7) + 1*(gr3^2+1e-7)*(gr7^2+1e-7) + 0.99*(gr4^2+1e-7)*(gr5^2+1e-7) + 1*(gr4^2+1e-7)*(gr6^2+1e-7) + 1*(gr4^2+1e-7)*(gr7^2+1e-7) + 0.33*(gr5^2+1e-7)*(gr6^2+1e-7) + 1*(gr5^2+1e-7)*(gr7^2+1e-7) + 0.99*(gr6^2+1e-7)*(gr7^2+1e-7))/((gr0^2+1e-7)*(gr1^2+1e-7) + (gr0^2+1e-7)*(gr2^2+1e-7) + (gr0^2+1e-7)*(gr3^2+1e-7) + (gr0^2+1e-7)*(gr4^2+1e-7) + (gr0^2+1e-7)*(gr5^2+1e-7) + (gr0^2+1e-7)*(gr6^2+1e-7) + (gr0^2+1e-7)*(gr7^2+1e-7) + (gr1^2+1e-7)*(gr2^2+1e-7) + (gr1^2+1e-7)*(gr3^2+1e-7) + (gr1^2+1e-7)*(gr4^2+1e-7) + (gr1^2+1e-7)*(gr5^2+1e-7) + (gr1^2+1e-7)*(gr6^2+1e-7) + (gr1^2+1e-7)*(gr7^2+1e-7) + (gr2^2+1e-7)*(gr3^2+1e-7) + (gr2^2+1e-7)*(gr4^2+1e-7) + (gr2^2+1e-7)*(gr5^2+1e-7) + (gr2^2+1e-7)*(gr6^2+1e-7) + (gr2^2+1e-7)*(gr7^2+1e-7) + (gr3^2+1e-7)*(gr4^2+1e-7) + (gr3^2+1e-7)*(gr5^2+1e-7) + (gr3^2+1e-7)*(gr6^2+1e-7) + (gr3^2+1e-7)*(gr7^2+1e-7) + (gr4^2+1e-7)*(gr5^2+1e-7) + (gr4^2+1e-7)*(gr6^2+1e-7) + (gr4^2+1e-7)*(gr7^2+1e-7) + (gr5^2+1e-7)*(gr6^2+1e-7) + (gr5^2+1e-7)*(gr7^2+1e-7) + (gr6^2+1e-7)*(gr7^2+1e-7))*(4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-06'
    derivative_order = 2
  []
  # --- 2a + 2b 合成晶界迁移率 L ---
  # 拆成三层是为了让每个材料的符号求导树都小；
  # 链式法则由 material_property_names 自动完成（含二阶）。
  # derivative_order=2 是必须的：ACInterface 要 dL/dop 与 d2L/dop2。
  [L_aniso]
    type = DerivativeParsedMaterial
    property_name = L
    material_property_names = 'L2a L2b'
    expression = 'L2a*L2b'
    derivative_order = 2
  []
  # 【2026-09-17 同步 Ti64 参数】
  #   sigma = 0.6 J/m^2 (Gornakova & Prokofjev 2020)
  #   mu0   = 6*sigma/wGB   = 9.0e5
  #   kappa = 0.75*sigma*wGB = 1.8e-6
  # 【2026-09-17 同步 Arrhenius】晶界迁移率 L 改为温度相关
  #   M_GB = GBmob0*exp(-Q/(kb*T))，L = 4/3*M_GB/wGB
  #   Ti64 beta: GBmob0 = 232 m^4/(J*s), Q = 3.234 eV
  #   （出处见 stage1_meltpool_ti64.i 的详细注释）
  #   **M0 与 Q 必须成对替换**，只换一个一定错。
  # 温度相关的势垒 mu —— 熔池内变负（熔化开关）
  [barrier_mu]
    type = DerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
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
  #   c 的界面宽：w_c = sqrt(kappa_c/f'') ≈ 2.5 um（2.5 个单元）
  #
  #   代价：溶质扩散长度 sqrt(D*t) 在 t=8e-4 s 时约 2 um，剖面很锐 ——
  #   这反而更接近 LPBF 的真实情形（真实溶质边界层只有 ~8 nm）。
  [ch_params]
    type = GenericConstantMaterial
    prop_names  = 'M        kappa_c'
    prop_values = '2.8e-9   1.125e-11'
  []

  # 溶质自由能：给出液相/固相分凝
  #   常数已随 F0 同步缩放：k_c 9.0e5->0.9, A_part 4.5e5->0.45
  #   （A_part = k_c/2 保持分配系数 k = 0.5 不变）
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '0.9 0.35 0.45'
    expression = 'k_c/2*(c-c0)^2
                  + A_part*c^2*(gr0^2+gr1^2+gr2^2+gr3^2
                                +gr4^2+gr5^2+gr6^2+gr7^2)'
    derivative_order = 2
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
  # --- 2a/2b 诊断（smoke test 用，确认各向异性真的在起作用）---
  #   align4 = cos^2(2(phi-theta))：1 = 晶粒易生长轴与热梯度完全对齐
  #   若这个量的时间平均始终是常数，说明 2b 没生效
  [align_mean]
    type = ElementAverageValue
    variable = grad_align
    execute_on = 'initial timestep_end'
  []
  [align_max]
    type = ElementExtremeValue
    variable = grad_align
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [align_min]
    type = ElementExtremeValue
    variable = grad_align
    value_type = min
    execute_on = 'initial timestep_end'
  []
  # 局部取向场的两个分量 —— 与 extract.py 反解出的 theta 交叉校验
  [oc_mean]
    type = ElementAverageValue
    variable = orient_cos
    execute_on = 'initial timestep_end'
  []
  [os_mean]
    type = ElementAverageValue
    variable = orient_sin
    execute_on = 'initial timestep_end'
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

  l_max_its = 30
  l_tol = 1e-6
  nl_max_its = 50
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-7

  end_time = 6.5e-4

  # 【关键】界面弛豫时间 ~4.7e-6 s；不加 dtmax 会发散
  dtmax = 2e-6

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-6
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
    time_step_interval = 1
    file_base = stage1d
  []
[]
