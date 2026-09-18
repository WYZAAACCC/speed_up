#!/bin/bash
# 【C4 动态测量】移动界面下的溶质分凝 —— 第一版（平衡态）测不到的那个问题。
#
# 【为什么要重做】第一版量的是**平衡态** k 随分辨率的变化，`w/dx=1…16` 全部
# 精确给出 0.6303 —— 因为平衡态 V=0，根本没有边界层，原理上看不到动态截留。
#
# 【本版设计】1D 定向凝固：温度场以恒定梯度 G 平移，速度 V。
#   T(x,t) = T_mid + G*(x - V*t)   => 熔点面（T=T_mid）以速度 V 向右移动
#   η 由熔化开关驱动：固相 η→1、液相 η→0，界面跟着温度面走
#   溶质因 k=0.63<1 被排出，在界面前沿堆积
#
#   量：界面**后方**（固相，刚凝固的）与**前方**（液相）的 c
#       稳态下 c_S/c_L 即有效分配系数
#
# 【变的是什么】网格分辨率 dx（界面宽 W 固定=4um，与生产一致）：
#   dx = 1.0, 0.5, 0.25, 0.125, 0.0625 um  =>  W/dx = 4, 8, 16, 32, 64
#   判据：若 c_S/c_L 随 dx 显著变化 -> 生产网格（W/dx=4）不可信，必须修
#         若已收敛            -> 模型有确定解，问题变成"这个解是否物理"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/trapdyn
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

cat > tpl.i <<'TPL'
# 1D 定向凝固：温度梯度平移，界面随之移动
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = NXPLACE
  xmin = 0
  xmax = 60e-6
[]

[Variables]
  [gr0]
  []
  [c]
  []
  [w]
  []
[]

[Functions]
  # 熔点面以速度 V 向右移动。初始时在 x=20e-6。
  [Tfn]
    type = ParsedFunction
    symbol_names = 'Tmid G V x0'
    symbol_values = '1903 1.0e7 VPLACE 20e-6'
    expression = 'Tmid + G*(x - x0 - V*t)'
  []
[]

[AuxVariables]
  [T]
  []
[]

[AuxKernels]
  [T_aux]
    type = FunctionAux
    variable = T
    function = Tfn
    execute_on = 'initial timestep_end'
  []
[]

[ICs]
  # 初始：左边固相 gr0=1，右边液相 gr0=0，界面在 x=20e-6
  [gr0_ic]
    type = FunctionIC
    variable = gr0
    function = '0.5*(1-tanh((x-20e-6)/2e-6))'
  []
  [c_ic]
    type = ConstantIC
    variable = c
    value = 0.036
  []
  [w_ic]
    type = ConstantIC
    variable = w
    value = 0
  []
[]

[Kernels]
  # η：Allen-Cahn + 界面能，驱动力来自熔化开关 mu(T)
  [gr0_dt]
    type = TimeDerivative
    variable = gr0
  []
  [gr0_bulk]
    type = ACGrGrPoly
    variable = gr0
    v = ''
    mob_name = L
  []
  [gr0_int]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
  []
  # 溶质：分裂式 Cahn-Hilliard
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
  [ch_params]
    type = GenericConstantMaterial
    prop_names = 'M kappa_c'
    prop_values = '2.8e-9 1.125e-11'
  []
  # 熔化开关：液相 mu<0 回退体驱动力
  [barrier_mu]
    type = DerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'T'
    constant_names = 'mu0 T_mid dT boost'
    constant_expressions = '9.0e5 1903 60 2'
    expression = 'mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT)))'
    derivative_order = 1
  []
  [const]
    type = GenericConstantMaterial
    prop_names = 'kappa_op gamma_asymm sigma L0 Q kb wGB'
    prop_values = '1.8e-6 1.5 0.6 232 3.234 8.617e-5 4e-6'
  []
  # L = 4/3 * M0 * exp(-Q/kbT)/wGB （与生产一致）
  [L_aniso]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T'
    material_property_names = 'L0 Q kb wGB'
    expression = '(4.0/3.0)*L0*exp(-Q/(kb*T))/wGB'
    derivative_order = 1
  []
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '0.9 0.036 0.264'
    expression = 'k_c/2*(c-c0)^2 + A_part*c^2*gr0^2'
    derivative_order = 2
  []
[]

[Postprocessors]
  # 界面位置（gr0=0.5 处）—— 用于确认界面真的在动
  [iface]
    type = FindValueOnLine
    start_point = '0 0 0'
    end_point = '60e-6 0 0'
    v = gr0
    target = 0.5
    tol = 1e-6
  []
  [c_max]
    type = ElementExtremeValue
    variable = c
  []
  [c_min]
    type = ElementExtremeValue
    variable = c
  []
  [T_at_iface]
    type = ElementalVariableValue
    variable = T
    elementid = 0
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-11
  nl_max_its = 20
  # 起始 dt 给小（ROADMAP 附录 A）。界面要走 20um，V=0.6 -> 需要 t~3.3e-5
  dt = 1e-9
  end_time = 3.0e-5
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-9
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 8
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
TPL

# 变网格：W/dx = 4, 8, 16, 32, 64  （W=4um，域长 60um）
python3 - <<'PY'
import os
V = 0.6
for tag, nx in (("d4",60),("d8",120),("d16",240),("d32",480),("d64",960)):
    s = open("tpl.i", encoding="utf-8").read()
    s = s.replace("NXPLACE", str(nx)).replace("VPLACE", str(V))
    os.makedirs(tag, exist_ok=True)
    open(f"{tag}/t.i","w",encoding="utf-8").write(s)
    print(f"  {tag}: nx={nx}  dx={60e-6/nx*1e6:.4f} um  W/dx={4e-6/(60e-6/nx):.0f}")
PY

echo
echo "=== 串行跑 5 个分辨率 ==="
for T in d4 d8 d16 d32 d64; do
  ( cd "$T" && setsid --wait "$MOOSE" -i t.i > run.log 2>&1; echo "$T rc=$?" >> "$D/rc.txt" )
done

echo
echo "================ 动态溶质分凝 vs 网格 ================"
python3 - <<'PY'
import csv, os
print(f"  {'变体':<6}{'W/dx':<7}{'末时刻':>12}{'界面位置':>12}{'c_max':>12}{'c_min':>12}{'k_eff':>10}")
for tag, wdx in (("d4",4),("d8",8),("d16",16),("d32",32),("d64",64)):
    p = f"/root/work/trapdyn/{tag}/t_out.csv"
    if not os.path.exists(p):
        print(f"  {tag:<6}{wdx:<7}  无输出"); continue
    rows = list(csv.DictReader(open(p)))
    if not rows: continue
    r = rows[-1]
    try:
        cmax, cmin = float(r["c_max"]), float(r["c_min"])
        ifc = float(r["iface"])
        t = float(r["time"])
    except (KeyError, ValueError):
        print(f"  {tag:<6}{wdx:<7}  字段缺失: {list(r)[:8]}"); continue
    keff = cmin/cmax if cmax else float("nan")
    print(f"  {tag:<6}{wdx:<7}{t:>12.4e}{ifc*1e6:>11.2f}um{cmax:>12.6f}{cmin:>12.6f}{keff:>10.4f}")
PY
echo
echo "  判据：k_eff = c_min/c_max（固相/液相）。目标 0.63。"
echo "        若 k_eff 随 W/dx 显著变化 -> 生产网格（W/dx=4）不可信。"
