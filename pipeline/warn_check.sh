#!/bin/bash
# 查 MOOSE 运行日志里的告警 —— 低级问题最容易藏在这里
DL=/root/work/s1d_w/run.log       # 最新 D 版（带 print_linear_residuals）
[ -f "$DL" ] || DL=/root/work/s1d_smoke/run.log
CL=/root/work/s1c_col/run.log     # C 版对照

for pair in "D版:$DL" "C版:$CL"; do
  tag="${pair%%:*}"; L="${pair#*:}"
  echo "################ $tag ($L) ################"
  if [ ! -f "$L" ]; then echo "  日志不存在"; continue; fi
  echo "--- 告警/警告 ---"
  grep -a -i -E "warning|警告|not declared|not initialized|not found|deprecated|unused|singular|ill-conditioned" "$L" \
    | grep -a -v "Warning: Ambient" | head -12
  echo "--- 线性求解状态 ---"
  grep -a -E "Linear solve|linear iterations|CONVERGED_RTOL|DIVERGED" "$L" | head -8
  echo
done
