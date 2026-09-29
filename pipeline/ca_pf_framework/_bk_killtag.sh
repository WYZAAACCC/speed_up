#!/bin/bash
# _bk_killtag.sh <pattern> —— 按命令行匹配杀进程（**按 PID**，不用 pkill -f）
set -u
pat=${1:?需要 pattern}
for p in $(ps -e -o pid,cmd --no-headers | grep -F "$pat" | grep -v grep | awk '{print $1}'); do
  kill -9 "$p" 2>/dev/null && echo "killed $p"
done
sleep 2
echo "--- 剩余 ---"
ps -e -o pid,cmd --no-headers | grep -F "$pat" | grep -v grep | cut -c1-60
