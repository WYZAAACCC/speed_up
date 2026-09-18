#!/bin/bash
# 补齐上次探针的缺口：上次只测到 derivative_order = 1，
# 而 ACInterface 真正要的是 **二阶** 导数 (d2L/dop2)。
# 这里造一个最小多晶问题，用 ACInterface + ACGrGrPoly，
# 让 L 依赖一个 AuxVariable，再用 -snes_test_jacobian 验雅可比。
#
#   A: L = 1 + 0.5*u^2                      coupled_variables = 'u'
#   B: L = 1 + 0.5*u^2*a   (a 是恒 1 的 FunctionAux)   coupled_variables = 'u a'
# 两者数学上完全相同（a≡1），dL/du 与 d2L/du2 也相同。
# 若 B 的雅可比误差远大于 A，就坐实了"二阶导 + Aux 耦合"会出错。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_aux2
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

mk() {
cat > "$1.i" <<EOF
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 4
  ny = 4
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
  [a]
    order = CONSTANT
    family = MONOMIAL
  []
  [b]
    order = CONSTANT
    family = MONOMIAL
  []
  [c]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[Functions]
  [one]
    type = ParsedFunction
    expression = '1'
  []
[]
[AuxKernels]
  [a]
    type = FunctionAux
    variable = a
    function = one
    execute_on = 'initial timestep_end'
  []
  [b]
    type = FunctionAux
    variable = b
    function = one
    execute_on = 'initial timestep_end'
  []
  [c]
    type = FunctionAux
    variable = c
    function = one
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
  []
[]
[Kernels]
  [gr0]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr0 gr1'
    mu = mu
    gamma = gamma_asymm
    mob_name = L
  []
  [gr1]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0 gr1'
    mu = mu
    gamma = gamma_asymm
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
  num_steps = 1
  petsc_options_iname = '-snes_test_jacobian'
  petsc_options_value = '1'
[]
EOF
}

mk A 'gr0 gr1'        '1+0.5*(gr0^2+gr1^2)'
mk B 'gr0 gr1 a b c'  '1+0.5*(gr0^2+gr1^2)*a*b*c'

echo "A: L = 1+0.5*(gr0^2+gr1^2)          （无 Aux 耦合）"
echo "B: L = 1+0.5*(gr0^2+gr1^2)*a*b*c    （a=b=c=1，数学上完全相同）"
echo
for t in A B; do
  echo "=============== $t ==============="
  out=$("$MOOSE" -i "$t.i" 2>&1)
  echo "$out" | grep -a "J - Jfd" | head -3
  echo "$out" | grep -a -m1 -E '\*\*\* ERROR' && echo "$out" | grep -a -m2 -A2 'ERROR' | head -6
done
