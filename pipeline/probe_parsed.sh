#!/bin/bash
# 最小对照实验：DerivativeParsedMaterial 到底认不认 x / y / t
# 每个变体单独跑 --check-input，只看能不能构造出来。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_parsed
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

for expr in 'u*u' 'x' 'y' 't' 'x+y+t+u*u' 'sqrt(x^2+y^2)'; do
  cat > in.i <<EOF
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
[Materials]
  [m]
    type = DerivativeParsedMaterial
    property_name = f
    coupled_variables = 'u'
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
  out=$("$MOOSE" -i in.i --check-input 2>&1)
  if echo "$out" | grep -q 'Unknown identifier'; then
    verdict="不认"
  elif echo "$out" | grep -qi 'error'; then
    verdict="其他错误: $(echo "$out" | grep -i -m1 error | cut -c1-110)"
  else
    verdict="认"
  fi
  printf '  expression = %-20s -> %s\n' "'$expr'" "$verdict"
done
