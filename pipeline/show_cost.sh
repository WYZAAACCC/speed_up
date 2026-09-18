#!/bin/bash
# 展示成本分解各变体的进度与读数（内联 for 里的 $T 会被吞，必须写脚本）。
echo "  变体  步数  牛顿  雅可比均值   墙钟      说明"
echo "  ---------------------------------------------------------------"
desc() { case $1 in V0) echo "完整基线";; V1) echo "去各向异性材料";; V2) echo "去溶质 c/w";; V3) echo "去两者";; esac; }
for T in V0 V1 V2 V3; do
  L=/root/work/cost/$T/run.log
  if [ ! -f "$L" ]; then echo "  $T   （尚未开始）"; continue; fi
  NS=$(grep -ac '^Time Step' "$L")
  NJ=$(grep -ac 'Nonlinear |R|' "$L")
  JM=$(sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1;n++} END{if(n>0)printf "%.1f", s/n; else print "?"}')
  W=$(sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Finished Executing[^]]*\] \[ *[0-9.]+ s\]' | grep -oE '[0-9.]+' | head -1)
  [ -z "$W" ] && W="进行中"
  printf "  %-5s %-5s %-5s %-12s %-10s %s\n" "$T" "$NS" "$NJ" "$JM" "$W" "$(desc $T)"
done
echo
if [ -f /root/work/cost/rc.txt ]; then echo "  rc 记录:"; sed 's/^/    /' /root/work/cost/rc.txt; fi
echo
ps -eo pid,etime,comm | grep phase_field | grep -v grep | sed 's/^/  进程: /'
