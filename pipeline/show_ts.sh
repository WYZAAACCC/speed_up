#!/bin/bash
# 看三个输入的 TimeStepper 配置（内联 for 循环里的 $F 会被 Git Bash->WSL 吞掉，必须写文件）。
for F in /root/work/slv_cmp/B/B.i /root/work/bench_full/bench.i /root/work/mpi_scale/mpi.i /root/work/diag_scale/g_lo.i; do
  echo "--- $F ---"
  sed -n '/\[TimeStepper\]/,/^\[\]/p' "$F" 2>/dev/null | head -14
  echo
done
