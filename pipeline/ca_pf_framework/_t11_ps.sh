#!/bin/bash
# _t11_ps.sh —— 把所有 python 进程写到文件（避免 shell/过滤坑）。
OUT=/mnt/f/speed_up/_w2_ps.txt
{
echo "############ $(date '+%F %T')"
echo "python 进程数: $(pgrep -x python | wc -l)"
for p in $(pgrep -x python); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  r=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  echo "  PID $p  RSS=${r}kB"
  echo "     $(echo "$c" | head -c 200)"
done
echo
echo "内存:"; free -m
} > "$OUT" 2>&1
cat "$OUT"
