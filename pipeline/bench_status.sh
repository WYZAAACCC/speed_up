#!/bin/bash
# 基准进度汇报。写成 .sh 跑 —— 内联命令里的中文引号 + $变量
# 在 Git Bash -> WSL 这条链上反复出问题。
echo "现在 $(date '+%H:%M:%S')  负载: $(uptime | sed 's/.*load average/load/')"
echo "MOOSE 进程数: $(ps -eo comm | grep -c phase_field)"
echo
for t in B0_serial B1_mumps B2_mpi4_mumps B3_mpi8_mumps B4_mpi8_asm; do
  L="/root/work/s1d_bench/$t/run.log"
  printf "%-16s " "$t"
  if [ -f "$L" ]; then
    printf "收敛步=%-3s 牛顿末: " "$(grep -ac 'Solve Converged' "$L")"
    grep -a "Nonlinear |R|" "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -1
    grep -a -m1 -E '\*\*\* ERROR|out of memory|MPI_ABORT|Aborting' "$L" | sed 's/^/                  !! /'
  else
    echo "无日志"
  fi
done
echo
echo "=== 生产跑 ==="
tail -2 /root/work/rn.log 2>/dev/null
echo "=== 基准总耗时计时 ==="
grep -a -E "^real" /root/work/bs.log 2>/dev/null || echo "  仍在跑（尚未输出 time）"
