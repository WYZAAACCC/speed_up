#!/bin/bash
# 精确按 PID 杀：只杀指定的探测进程
for P in "$@"; do
  if [ -d "/proc/$P" ]; then
    echo "kill $P : $(tr '\0' ' ' < /proc/$P/cmdline)"
    kill -9 "$P" 2>/dev/null
  fi
done
sleep 3
echo "=== 剩余 ==="
ps -eo pid,etimes,rss,args | grep -E "_r1_|_probe" | grep -v grep
echo "=== mem ==="
free -g
