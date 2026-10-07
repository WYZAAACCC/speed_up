#!/bin/bash
# _r87_load.sh —— 查 `_w2_r41dg.log`（20.12 s/步的那个离群点）当时的**并发负载**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 09:00–09:20 窗口内被写过的 _w2_*.log（活跃作业的指纹）"
ls -la --time-style='+%H:%M:%S' _w2_*.log 2>/dev/null | awk '$6 >= "08:55:00" && $6 <= "09:25:00" {print "  "$6"  "$5" B  "$7}'
echo
echo "=== r41dg 自己的时间戳与内容"
ls -la --time-style='+%H:%M:%S' _w2_r41dg.log
echo "  步数读数：$(grep -c 's/步' _w2_r41dg.log)"
grep -o '\[ *[0-9]*\].*s/步' _w2_r41dg.log
echo
echo "=== 同一时期 r41 系列其它日志的耗时（对照：同 N/同 nreg）"
for f in _w2_r41*.log _w2_r40*.log; do
  [ -f "$f" ] || continue
  n=$(grep -c 's/步' "$f")
  [ "$n" -gt 0 ] || continue
  printf '  %-26s %s 行  中位 %s s/步\n' "$f" "$n" "$(grep -o '[0-9.]*s/步' "$f" | tr -d 's/步' | sort -n | awk '{a[NR]=$1} END{print a[int(NR/2)+1]}')"
done
echo
echo "=== r41dg 是否被中途杀掉（末行不是终态）"
tail -3 _w2_r41dg.log
