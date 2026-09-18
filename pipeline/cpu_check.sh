#!/bin/bash
# 查 CPU 核数 + 当前 MOOSE 进程占用 + 基准进度。
# 【背景】用户反映"CPU 负载很低"。根因：MOOSE 默认单进程单线程（只有 main + 1 个 futex
# 线程），一个进程只用 1 个核。要跑满机器必须用 MPI（mpiexec -n N）。
echo "=========== CPU 资源 ==========="
echo "WSL 可见逻辑核数 = $(nproc)"
lscpu | grep -E 'Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket'
echo
echo "=========== 当前 MOOSE 进程 ==========="
for P in $(pgrep -f phase_field-opt); do
  CPU=$(awk '{printf "%.1f", ($14+$15)/100}' /proc/$P/stat 2>/dev/null)
  RSS=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-i [^ ]+' | head -1)
  NTH=$(ls /proc/$P/task 2>/dev/null | wc -l)
  echo "  PID=$P  已用CPU=${CPU}s  RSS=$((RSS/1024))MB  线程=$NTH  $CMD"
done
echo
echo "=========== 系统整体 ==========="
uptime
echo
echo "=========== 基准进度 ==========="
for D in /root/work/bench_full /root/work/slv_cmp/A /root/work/slv_cmp/B; do
  echo "--- $D ---"
  if [ -f "$D/run.log" ]; then
    sed 's/\x1b\[[0-9;]*m//g' "$D/run.log" | tail -6 | sed 's/^/    /'
  else
    echo "    无日志"
  fi
done
