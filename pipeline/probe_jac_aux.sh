#!/bin/bash
# 最小对照实验：把 AuxVariable 耦合进 DerivativeParsedMaterial
# 会不会让**对真实解变量的导数**出错？
#
# 两个输入的物理与真值**完全相同**：
#   A: F = 1 + u^2            coupled_variables = 'u'
#   B: F = 1 + u^2 * a        coupled_variables = 'u a'，其中 a 是恒为 1 的 FunctionAux
# 两者 dF/du 都等于 2u。用 PETSc 的 -snes_test_jacobian 把装配出的雅可比
# 与有限差分雅可比对比。若 B 的误差远大于 A，就证明 AuxVariable 耦合会污染导数。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_jac
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

mk() {   # $1=标签  $2=coupled  $3=expression
cat > "$1.i" <<EOF
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 3
  ny = 3
[]
[Variables]
  [u]
  []
[]
[AuxVariables]
  [a]
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
[]
[Materials]
  [F]
    type = DerivativeParsedMaterial
    property_name = F
    coupled_variables = '$2'
    expression = '$3'
    derivative_order = 1
  []
[]
[Kernels]
  [diff]
    type = MatDiffusion
    variable = u
    diffusivity = F
  []
  [src]
    type = BodyForce
    variable = u
    value = 1
  []
[]
[BCs]
  [bc]
    type = DirichletBC
    variable = u
    boundary = 'left right top bottom'
    value = 0
  []
[]
[Problem]
  type = FEProblem
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  petsc_options_iname = '-snes_test_jacobian'
  petsc_options_value = '1'
[]
[Outputs]
  csv = true
[]
EOF
}

mk A 'u'      '1+u^2'
mk B 'u a'    '1+u^2*a'

echo "两个输入的真值导数都是 dF/du = 2u，物理完全相同。"
echo
for t in A B; do
  echo "=========== $t ==========="
  grep -A1 "coupled_variables" "$t.i" | head -2
  out=$("$MOOSE" -i "$t.i" 2>&1)
  echo "$out" | grep -a -E "Testing Jacobian|J - Jfd|Norm of matrix|norm ratio" | head -6
  # 有些版本不带 "Testing Jacobian" 前缀，兜底抓 Jfd 行
  [ -z "$(echo "$out" | grep -a 'Jfd')" ] && echo "  (没抓到 Jfd 行，原始输出尾部：)" && echo "$out" | tail -6
done
