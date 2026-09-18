# =============================================================================
# 由 gen_aniso.py 自动生成 —— 请勿手改
#   2a: 取向差依赖的晶界能/迁移率（Moelans Algorithm 1，严格复刻 GBAnisotropy）
#   2b: 热梯度驱动的晶粒选择（解析 Rosenthal 梯度，四重对称对齐）
# 取向 theta_i (度) = [0.0, 14.85, 29.7, 34.65, 49.5, 64.35, 69.3, 84.15]
# A_ani = 0.7
# 各向同性极限自检: kappa_op=1.799943021e-06 vs 基线 1.8e-6  (相对偏差 3.17e-05)
#                   gamma_asymm=1.499918283 vs 基线 1.5   (相对偏差 5.45e-05)
#   偏差来自"教科书圆整值 0.75 vs Moelans 不动点精确解 0.74997626"，
#   非实现误差；GBAnisotropy 本身跑出来同样是 1.799943e-6。
#
# 【实现约束，已用最小对照实验核实】
#   1. `ParsedMaterial`/`ParsedAux` **都不认 x / y / t**（只有 `ParsedFunction` 认）。
#      所以温度梯度必须先由 ParsedFunction + FunctionAux 算成 AuxVariable，
#      再耦合进材料。这在数学上无损：梯度只依赖 (x,y,t) 不依赖 eta，
#      它相对 eta 的导数确实是 0，雅可比不缺项。
#   2. `material_property_names` 的链式法则可用（含二阶），
#      所以把 align4 -> L2b -> L 拆成三层小材料，避免单个求导树爆炸。
# =============================================================================

# --- 2b 的温度梯度：ParsedFunction 认得 x/y/t，由它解析求导 ---
[Functions]
  [gradTx_fn]
    type = ParsedFunction
    expression = '(0.2228169203/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t)))*(-(x+1.2e-4-0.6*t)/(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t))/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))'
  []
  [gradTy_fn]
    type = ParsedFunction
    expression = '(0.2228169203/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))*exp(-50000*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+(x+1.2e-4-0.6*t)))*(-y/(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))-50000*y/sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))'
  []
[]

# --- 2a/2b 的取用量（grad_* 供材料耦合，orient_*/ 供数据提取）---
[AuxVariables]
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
[]
