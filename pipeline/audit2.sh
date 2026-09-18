#!/bin/bash
# 补齐审计：求解器、IC、后处理。内联 grep 的 ^\[ 会被 Git Bash 吞，必须写脚本。
S=/mnt/f/speed_up/pipeline/stage1_meltpool_c.i
echo "=== 全部 section 头 ==="
grep -n '^\[' "$S" | sed 's/^/  /'
echo
echo "=== 求解器块 ==="
sed -n '/^\[Executioner\]/,/^\[Outputs\]/p' "$S" | grep -vE '^\s*#|^\s*$' | sed 's/^/  /'
echo
echo "=== IC 块 ==="
sed -n '/^\[ICs\]/,/^\[UserObjects\]/p' "$S" | grep -vE '^\s*#|^\s*$' | sed 's/^/  /'
echo
echo "=== 后处理 ==="
sed -n '/^\[Postprocessors\]/,/^\[Preconditioning\]/p' "$S" | grep -E '^  \[|type =' | sed 's/^/  /'
echo
echo "=== 输出 ==="
sed -n '/^\[Outputs\]/,$p' "$S" | grep -vE '^\s*#|^\s*$' | head -14 | sed 's/^/  /'
