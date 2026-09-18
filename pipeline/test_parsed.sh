#!/bin/bash
# 二分找出 ParsedSubdomainMeshGenerator 的表达式里哪个标识符不被认识
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
BIN=/root/moose/modules/phase_field/phase_field-opt
cd /root/work || exit 1
mkdir -p ptest && cd ptest || exit 1

try() {
    local desc="$1" expr="$2"
    cat > t.i <<EOF
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 4
    ny = 4
    xmin = -1
    xmax = 1
    ymin = 0
    ymax = 1
  []
  [sub]
    type = ParsedSubdomainMeshGenerator
    input = gen
    combinatorial_geometry = '$expr'
    block_id = 1
    block_name = liq
  []
[]
[Variables]
  [u]
  []
[]
[Kernels]
  [d]
    type = Diffusion
    variable = u
  []
[]
[Executioner]
  type = Steady
[]
EOF
    out=$("$BIN" -i t.i --check-input 2>&1)
    if echo "$out" | grep -q 'Syntax OK'; then
        printf "  [OK  ] %-34s | %s\n" "$desc" "$expr"
    else
        msg=$(echo "$out" | grep -A3 'ERROR' | grep -i 'syntax\|unknown' | head -1)
        printf "  [FAIL] %-34s | %s  <<< %s\n" "$desc" "$expr" "$msg"
    fi
}

echo "逐个测试表达式成分："
try "纯 x"                 'x < 0'
try "x,y 都用"             'x^2+y^2 < 1'
try "sqrt"                 'sqrt(x^2+y^2) < 1'
try "科学计数 1e-4"         'x < 1e-4'
try "科学计数 1.2e-4"       'x < 1.2e-4'
try "pi"                   'x < pi'
try "exp"                  'exp(x) < 1'
try "abs"                  'abs(x) < 1'
try "比较 >"               'x > -1'
try "负号+科学计数"          'x > -1.2e-4'
try "exp(-50000*(...))"    'exp(-50000*(sqrt(x^2+y^2)+x)) < 1'
try "完整表达式(折叠常数)"    '0.222817/sqrt((x+1.2e-4)^2+y^2+1e-12)*exp(-50000*(sqrt((x+1.2e-4)^2+y^2+1e-12)+x+1.2e-4)) > 1628'
try "带 pi 的完整式"         '28/(2*pi*20*sqrt((x+1.2e-4)^2+y^2+1e-12))*exp(-0.6*(sqrt((x+1.2e-4)^2+y^2+1e-12)+x+1.2e-4)/(2*6e-06)) > 1628'
