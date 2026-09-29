#!/bin/bash
# _bk_killall.sh —— 杀掉全部 `_bk_exp.py`（**按 PID、不走 pkill -f**，见 AGENTS.md §3.10：
#   `pkill -f` 会匹配到含该字符串的**自己的 shell**）。杀完打印残留核查。
set -u
echo "--- 杀之前 ---"
for P in $(pgrep -f '_bk_exp.py'); do
  echo "pid=$P tag=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -o 'tag [a-zA-Z0-9_]*' | head -1)"
done
for P in $(pgrep -f '_bk_exp.py'); do kill -9 "$P" 2>/dev/null; done
sleep 4
echo "--- 杀之后（应为空）---"
LEFT=0
for P in $(pgrep -f '_bk_exp.py'); do
  LEFT=$((LEFT+1))
  echo "残留 pid=$P cwd=$(readlink /proc/$P/cwd 2>/dev/null)"
done
echo "残留数 = $LEFT"
uptime
