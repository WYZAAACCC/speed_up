#!/bin/bash
# 验证两件事（2b 的实现完全依赖它们）：
#   A. ParsedAux 是否认得 x / y / t
#   B. DerivativeParsedMaterial 能否通过 material_property_names
#      把子材料的导数用链式法则组合起来（拆开大表达式、避免求导树爆炸）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_chain
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

echo "=== A. ParsedAux 是否认 x / y / t ==="
for expr in 'x' 'y' 't' 'x+y+t' 'exp(-x)*sqrt(y^2+1e-10)'; do
  cat > a.i <<EOF
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 2
  ny = 2
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
[AuxKernels]
  [a]
    type = ParsedAux
    variable = a
    expression = '$expr'
  []
[]
[Problem]
  solve = false
[]
[Executioner]
  type = Steady
[]
EOF
  out=$("$MOOSE" -i a.i --check-input 2>&1)
  if echo "$out" | grep -q 'Unknown identifier'; then v="不认"
  elif echo "$out" | grep -qi 'error'; then v="其他错误: $(echo "$out" | grep -i -m1 error | cut -c1-90)"
  else v="认"; fi
  printf '  %-28s -> %s\n' "$expr" "$v"
done

echo
echo "=== B. 材料属性链式法则（material_property_names）==="
cat > b.i <<'EOF'
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 2
  ny = 2
[]
[Variables]
  [u]
  []
[]
[AuxVariables]
  [out]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[AuxKernels]
  [out]
    type = MaterialRealAux
    variable = out
    property = C
  []
[]
[Materials]
  [a]
    type = DerivativeParsedMaterial
    property_name = A
    coupled_variables = 'u'
    expression = 'u^2+1'
    derivative_order = 2
  []
  [b]
    type = DerivativeParsedMaterial
    property_name = B
    material_property_names = 'A'
    expression = '3*A'
    derivative_order = 2
  []
  # C = A*B  —— 二阶链式法则必须能穿过两层
  [c]
    type = DerivativeParsedMaterial
    property_name = C
    material_property_names = 'A B'
    expression = 'A*B'
    derivative_order = 2
  []
[]
[Problem]
  solve = false
[]
[Executioner]
  type = Steady
[]
EOF
out=$("$MOOSE" -i b.i --check-input 2>&1)
if echo "$out" | grep -qi 'error'; then
  echo "  失败："; echo "$out" | grep -i -m3 -E 'error|Unknown' | cut -c1-160
else
  echo "  成功：材料属性链式法则可用（可把大表达式拆成多个小材料）"
fi
