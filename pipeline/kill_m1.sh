#!/bin/bash
# 停掉 M1（AD + MUMPS）：已实测它牛顿只做线性爬行（12 次迭代降 2.7 倍），无望。
# 注意：必须放在 .sh 文件里 —— 内联命令里 pgrep -f "phase_field-opt -i M1.i"
# 会因为引号被吞而报 "only one pattern can be provided"。
for P in $(pgrep -f 'M1.i'); do
  echo "  杀掉 PID $P"
  kill -9 "$P" 2>/dev/null
done
sleep 2
echo "剩余 MOOSE 进程："
ps -eo pid,etime,comm | grep phase_field | grep -v grep | sed 's/^/  /'
echo "可用内存 $(free -g | awk 'NR==2{print $7}') GB"
