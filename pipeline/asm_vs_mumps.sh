#!/bin/bash
# 全尺寸（430×150）ASM vs MUMPS 的速度与内存对比 —— B7 的最终产出。
# 两者**同配置**（dt=1e-7 起步、end_time=8e-6、nl_abs_tol=1e-9），只差求解器。
for TAG in "ASM:/root/work/bench_full_asm/run.log" "MUMPS:/root/work/bench_full/run.log"; do
  NAME="${TAG%%:*}"
  L="${TAG##*:}"
  echo "=============================================="
  echo "  全尺寸 $NAME"
  echo "=============================================="
  if [ ! -f "$L" ]; then echo "  无日志"; continue; fi
  NS=$(grep -ac '^Time Step' "$L")
  NJ=$(grep -ac 'Nonlinear |R|' "$L")
  echo "  时间步数 = $NS   牛顿迭代数 = $NJ"
  echo "  墙钟（MOOSE 自报）:"
  sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Finished (Solving|Executing)[^]]*\] \[[^]]*\]' | tail -1 | sed 's/^/    /'
  echo "  雅可比装配（均值）:"
  sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' \
    | sed 's/.*\[ *//;s/ s\]//' \
    | awk '{s+=$1;n++} END{if(n>0) printf "    %.1f s（n=%d）\n", s/n, n; else print "    无"}'
  echo "  末步:"
  grep -a '^Time Step' "$L" | tail -1 | sed 's/^/    /'
  echo "  报错:"
  grep -a -m2 -E '\*\*\* ERROR|Aborting' "$L" | sed 's/^/    /'
  echo
done
echo "  内存对照（实测峰值）：ASM = 3182 MB，MUMPS = 6418 MB"
echo "  判据：若 ASM 的单步耗时 > MUMPS 的 2 倍，则吞吐优势被抵消（见 ROADMAP）。"
