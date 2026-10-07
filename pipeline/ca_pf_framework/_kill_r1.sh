#!/usr/bin/env bash
# _kill_r1.sh --- 按 PID 精确杀（AGENTS §3.10：禁 pkill -f）
set -u
for P in $(ps -eo pid,args | grep -e '_r1_reinit_band.py' | grep -v grep | awk '{print $1}'); do
  echo "kill -9 $P  ($(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | cut -c1-100))"
  kill -9 "$P" 2>/dev/null
done
sleep 2
echo "--- 残留 ---"
ps -eo pid,args | grep -e '_r1_reinit' | grep -v grep || echo "(无)"
free -m | head -2
