#!/bin/bash
# _bk_killr1.sh —— 停掉 R1 时代的驱动脚本与其子进程（**按 PID**，绝不用 pkill -f）
set -u
for p in $(pgrep -f '_r1_drive' 2>/dev/null); do kill -9 "$p" 2>/dev/null; echo "killed driver $p"; done
sleep 1
for p in $(ps -e -o pid,cmd --no-headers | grep -E '_r1_' | grep -v grep | awk '{print $1}'); do
  kill -9 "$p" 2>/dev/null; echo "killed $p"
done
sleep 5
echo "--- 剩余 ---"
ps -e -o pid,stat,cmd --no-headers | grep -E '_bk_|_r1_' | grep -v grep | cut -c1-60
echo "--- mem ---"
free -m | head -2
