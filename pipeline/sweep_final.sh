#!/bin/bash
# 性能旋钮扫描最终汇总 + B7/B8 状态。
echo "================ 性能选项汇总 ================"
awk '/性能选项汇总/,0' /root/work/po.log | head -12
echo
echo "================ 逐项结局 ================"
grep -aE '开始|rc=' /root/work/po.log | tail -12 | sed 's/^/  /'
echo
echo "================ B7 全尺寸 ASM ==============="
sed 's/\x1b\[[0-9;]*m//g' /root/work/bench_full_asm/run.log 2>/dev/null | grep -aE '^Time Step|Nonlinear \|R\|' | tail -5 | sed 's/^/  /'
echo "  MOOSE 自报内存峰值: $(grep -a -oE '\[ *[0-9]+ MB\]' /root/work/bench_full_asm/run.log 2>/dev/null | tr -d '[]MB ' | sort -n | tail -1) MB"
echo
echo "================ B8 MPI n=8 全尺寸 ==============="
sed 's/\x1b\[[0-9;]*m//g' /root/work/bench_mpi_mem/run.log 2>/dev/null | grep -aE '^Time Step|Nonlinear \|R\|' | tail -5 | sed 's/^/  /'
echo "  当前各进程 RSS 之和:"
SUM=0
for P in $(pgrep -f 'bm.i' 2>/dev/null); do
  R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  [ -n "$R" ] && SUM=$((SUM + R))
done
echo "    $((SUM/1024)) MB （$((SUM/1024/1024)) GB），进程数 $(pgrep -f 'bm.i' | wc -l)"
echo
echo "================ 系统 ==============="
free -g | head -2 | sed 's/^/  /'
ps -eo pid,etime,rss,comm | grep phase_field | grep -v grep | sed 's/^/  /'
