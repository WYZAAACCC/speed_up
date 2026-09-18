#!/bin/bash
# 提取逐变量残差。MOOSE 的格式是表头一行，随后每个变量一行缩进。
# 取**最后一次**收敛判定前的那个块（即收敛时刻的逐变量残差）。
for T in lo hi; do
  L="/root/work/diag_scale/g_$T/run.log"
  echo "=================================================="
  echo "  nl_abs_tol = $([ $T = lo ] && echo 1e-6 || echo 1e-9)"
  echo "=================================================="
  [ -f "$L" ] || { echo "  无日志"; continue; }
  echo "  收敛步 = $(grep -ac 'Solve Converged' "$L")"
  echo
  echo "  --- 每个时间步收敛时刻的逐变量残差 ---"
  sed 's/\x1b\[[0-9;]*m//g' "$L" | awk '
    /residual\|_2 of individual variables/ { inblk=1; buf=""; next }
    inblk && /^[ \t]+[A-Za-z_]/ {
      line=$0; sub(/^[ \t]+/, "", line)
      buf = buf "      " line "\n"; next
    }
    inblk && !/^[ \t]/ { inblk=0 }
    /Solve Converged/ { if (buf != "") printf "%s", buf; buf="" }
  ' | tail -40
  echo
done
