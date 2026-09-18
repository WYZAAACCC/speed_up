#!/bin/bash
# 从日志里量出"每个牛顿迭代的时间都花在哪"，作为加速讨论的事实依据。
for TAG in "全尺寸MUMPS:/root/work/bench_full/run.log" "全尺寸ASM:/root/work/bench_full_asm/run.log" "215x75 MUMPS:/root/work/perf_opt/P0/run.log"; do
  NAME="${TAG%%:*}"
  L="${TAG##*:}"
  echo "=============================================="
  echo "  $NAME"
  echo "=============================================="
  [ -f "$L" ] || { echo "  无日志"; continue; }
  NJ=$(grep -ac 'Nonlinear |R|' "$L")
  JN=$(grep -ac 'Computing Jacobian' "$L")
  # 【坑】先剥掉 ANSI 色码再匹配 —— 色码序列里含 '['，会让 [^[]* 提前终止
  JS=$(sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -a -oE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1; n++} END{if(n>0) printf "%.0f (n=%d, 均 %.1f)", s, n, s/n; else print "0"}')
  echo "  牛顿迭代数 = $NJ    雅可比装配次数 = $JN"
  echo "  雅可比装配总耗时 = ${JS} s"
  echo "  本次运行墙钟（从 MOOSE 自报末行取）:"
  grep -a -oE 'Finished (Solving|Executing)[^]]*\] \[[^]]*\]' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -1 | sed 's/^/    /'
  echo "  --- 线性求解统计（迭代数分布）---"
  grep -a 'Linear solve' "$L" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//' | sort | uniq -c | sort -rn | head -4 | sed 's/^/    /'
  echo "  --- 时间步 ---"
  grep -a '^Time Step' "$L" | tail -2 | sed 's/^/    /'
  echo
done
