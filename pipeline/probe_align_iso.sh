#!/bin/bash
# 最小多晶问题里隔离 align 因子（修正版）
#
# 【上一版为什么是坏的】
#   1. 没设 int_width -> PolycrystalVoronoi 默认锐界面，而 kappa_op=1.8e-6 /
#      mu=9e5 对应 4 um 的界面宽，与 1x1 的默认网格完全不相容 -> 基线都发散
#   2. theta 选了 0 和 45、梯度沿 x：两者 |cos2theta| 都等于 1，
#      对齐因子退化成常数 1.7，B 和 C 结果逐位相同 -> 什么都没测到
# 本版：网格用真实尺度（40x40 um，dx=1um，int_width=4um=4 个单元），
#       取向选 0 和 30 度（对齐度不同），梯度方向沿 x。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_iso2
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# theta0=0   -> ct2=1,  st2=0
# theta1=30  -> ct2=cos60=0.5, st2=sin60=0.866
# 对齐因子（新写法），梯度用符号 GX/GY 占位
ALIGN='((gr0^2*(1*(GX^2-GY^2)+0*(2*GX*GY))^2 + gr1^2*(0.5*(GX^2-GY^2)+0.8660254*(2*GX*GY))^2)/((gr0^2+gr1^2+1e-3)*(GX^2+GY^2)^2))'
# L 的 eta 依赖部分（用真实 Arrhenius 形状，T 固定 1900 K）
L2A='(4.0/3.0*232*0.001/4e-6*(1+0.5*(gr0^2+gr1^2)))'

mk() {
cat > "$1.i" <<EOF
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
[GlobalParams]
  op_num = 2
  var_name_base = gr
[]
[Variables]
  [PolycrystalVariables]
  []
[]
[AuxVariables]
  [gxa]
    order = CONSTANT
    family = MONOMIAL
  []
  [gya]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[Functions]
  [fx]
    type = ParsedFunction
    expression = '1.0'
  []
  [fy]
    type = ParsedFunction
    expression = '0.3'
  []
[]
[AuxKernels]
  [gxa]
    type = FunctionAux
    variable = gxa
    function = fx
    execute_on = 'initial timestep_end'
  []
  [gya]
    type = FunctionAux
    variable = gya
    function = fy
    execute_on = 'initial timestep_end'
  []
[]
[ICs]
  [ic0]
    type = PolycrystalColoringIC
    variable = gr0
    polycrystal_ic_uo = voronoi
    op_index = 0
  []
  [ic1]
    type = PolycrystalColoringIC
    variable = gr1
    polycrystal_ic_uo = voronoi
    op_index = 1
  []
[]
[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 2
    rand_seed = 10
    int_width = 4e-6
  []
[]
[Kernels]
  [gr0]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr0 gr1'
    mob_name = L
  []
  [gr1]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0 gr1'
    mob_name = L
  []
  [i0]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
  []
  [i1]
    type = ACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
  []
[]
[Materials]
  [k]
    type = GenericConstantMaterial
    prop_names = 'kappa_op gamma_asymm mu'
    prop_values = '1.8e-6 1.5 9.0e5'
  []
  [L]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = '$2'
    expression = '$3'
    derivative_order = 2
  []
  # 把 align4 单独暴露出来，便于确认它真的在变（不是常数）
  [al]
    type = ParsedMaterial
    property_name = align4
    coupled_variables = '$2'
    expression = '$4'
  []
[]
[AuxVariables]
  [al4]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[AuxKernels]
  [al4]
    type = MaterialRealAux
    variable = al4
    property = align4
    execute_on = 'initial timestep_end'
  []
[]
[Postprocessors]
  [align_min]
    type = ElementExtremeValue
    variable = al4
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [align_max]
    type = ElementExtremeValue
    variable = al4
    value_type = max
    execute_on = 'initial timestep_end'
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
  dt = 1e-6
  num_steps = 3
  dtmax = 2e-6
  nl_max_its = 12
  l_tol = 1e-6
  l_max_its = 30
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-7
[]
[Outputs]
  csv = true
  print_linear_residuals = true
[]
EOF
}

AL_B='((gr0^2*(1*(1.0^2-0.09)+0*(2*1.0*0.3))^2 + gr1^2*(0.5*(1.0^2-0.09)+0.8660254*(2*1.0*0.3))^2)/((gr0^2+gr1^2+1e-3)*(1.0^2+0.09)^2))'
AL_C='((gr0^2*(1*(gxa^2-gya^2)+0*(2*gxa*gya))^2 + gr1^2*(0.5*(gxa^2-gya^2)+0.8660254*(2*gxa*gya))^2)/((gr0^2+gr1^2+1e-3)*(gxa^2+gya^2)^2))'

mk A 'gr0 gr1' "$L2A" '1'
mk B 'gr0 gr1' "$L2A*(1+0.7*(2*$AL_B-1))" "$AL_B"
mk C 'gr0 gr1 gxa gya' "$L2A*(1+0.7*(2*$AL_C-1))" "$AL_C"

echo "A: L 只依赖 eta（基线）"
echo "B: L 乘 align 因子，梯度为常数 (1.0, 0.3)"
echo "C: L 乘 align 因子，梯度来自 FunctionAux"
echo
for t in A B C; do
  echo "=============== $t ==============="
  timeout 300 "$MOOSE" -i "$t.i" > "$t.log" 2>&1
  echo "  退出码 $?"
  printf "  收敛步="; grep -ac "Solve Converged" "$t.log"
  grep -a "Nonlinear |R|" "$t.log" | head -8 | sed 's/^/    /'
  echo "  align4 范围（应在 0~1 且不是常数）:"
  grep -a -A3 "align_min" "$t.log" | head -6 | sed 's/^/    /'
  grep -a -m1 -E '\*\*\* ERROR' "$t.log" | sed 's/^/  /'
  echo
done
