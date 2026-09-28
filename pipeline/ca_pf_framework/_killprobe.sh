#!/usr/bin/env bash
# _killprobe.sh --- 安全清掉 _probe_shape / _run_box24 的残留进程
# ⚠ 按**精确进程名 + 逐 PID** 杀，不用 `pkill -f`（AGENTS §3.10：会杀掉自己）。
set -u
for P in $(ps -eo pid,args | grep -e '_probe_shape.py' -e '_run_box24.sh' | grep -v grep | awk '{print $1}'); do
  echo "kill -9 $P  ($(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | cut -c1-90))"
  kill -9 "$P" 2>/dev/null
done
sleep 3
echo "--- 残留 ---"
ps -eo pid,args | grep -e '_probe_shape' -e '_run_box24' | grep -v grep || echo "(无，已清干净)"
free -g | head -2
