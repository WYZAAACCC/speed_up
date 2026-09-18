#!/bin/bash
# 停掉 bench.i（全尺寸 MUMPS 长跑）。
#
# 理由：
#   1. 它已跑 1h37m 才到 t=1.3e-6（目标 8e-6），跑完还要约 10 小时
#   2. 它的目的（MUMPS 全尺寸的每迭代耗时）正被 verify_asm_win.sh 的
#      **串行短复测**覆盖，后者更干净
#   3. **它在争用 CPU，会污染那个干净复测** —— 这是停它的主要理由
#
# 【坑】必须放在 .sh 文件里：内联 pgrep -f 会因引号被吞而失败。
for P in $(pgrep -f 'bench.i'); do
  echo "  杀掉 bench.i PID=$P"
  kill -9 "$P" 2>/dev/null
done
sleep 2
echo "剩余 MOOSE 进程："
ps -eo pid,etime,comm | grep phase_field | grep -v grep | sed 's/^/  /'
echo "可用内存 $(free -g | awk 'NR==2{print $7}') GB"
