#!/bin/bash
# R49: 按 PID 精确杀掉 mb1s62（不用 pkill -f，见 AGENTS.md §3.10）
set -u
for P in 26221 26202; do
  if [ -d /proc/$P ]; then
    CWD=$(readlink /proc/$P/cwd 2>/dev/null)
    CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | cut -c1-80)
    echo "kill $P  cwd=$CWD"
    echo "        cmd=$CMD"
    kill -9 "$P" 2>/dev/null && echo "        -> killed"
  else
    echo "$P not alive"
  fi
done
sleep 2
echo "--- 残留检查（应只剩 cln11 / mb1L / mb1Ls 三条）"
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-120
