#!/bin/bash
# 对比全尺寸下 MUMPS 与 ASM 的内存占用 —— B7 的核心产出。
# 【B7 为什么关键】吞吐受内存限制：MUMPS 6.4 GB/条 => 21 GB 只能并发 3 条。
# 若 ASM 只要 2-3 GB，就能并发 6-10 条，吞吐反超 MPI 方案，且不牺牲物理
# （已证同容差下 ASM 与 MUMPS 解相同，relL2 ~1e-15）。
echo "=============== 全尺寸 ASM (B7) ==============="
for P in $(pgrep -f bench_asm.i); do
  R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  echo "  PID=$P  RSS = $((R/1024)) MB"
done
echo "  --- 进度 ---"
sed 's/\x1b\[[0-9;]*m//g' /root/work/bench_full_asm/run.log 2>/dev/null | grep -aE '^Time Step|Nonlinear \|R\||Computing Jacobian' | tail -8 | sed 's/^/    /'
echo "  --- 报错 ---"
grep -a -m3 -E '\*\*\* ERROR|Aborting' /root/work/bench_full_asm/run.log 2>/dev/null | sed 's/^/    /'

echo
echo "=============== 全尺寸 MUMPS (对照) ==============="
for P in $(pgrep -f 'bench.i'); do
  R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  echo "  PID=$P  RSS = $((R/1024)) MB"
done
echo "  MOOSE 自报峰值:"
grep -a -oE '\[ *[0-9]+ MB\]' /root/work/bench_full/run.log 2>/dev/null | tr -d '[]MB ' | sort -n | tail -1 | sed 's/^/    /'
echo "  --- 进度 ---"
sed 's/\x1b\[[0-9;]*m//g' /root/work/bench_full/run.log | grep -aE '^Time Step' | tail -3 | sed 's/^/    /'

echo
echo "=============== 系统内存 ==============="
free -g | head -2 | sed 's/^/  /'
echo
echo "=============== 性能扫描 ==============="
grep -aE '开始|rc=' /root/work/po.log | tail -6 | sed 's/^/  /'
