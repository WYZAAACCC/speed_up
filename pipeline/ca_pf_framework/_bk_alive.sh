#!/usr/bin/env bash
# _bk_alive.sh —— 检查还在跑的 _bk_exp 进程（状态 + 内存 + cwd）
set -u
echo "--- _bk_exp 进程 ---"
for P in $(pgrep -f 'python -u _bk_exp'); do
  ST=$(awk '{print $3}' /proc/$P/stat 2>/dev/null)
  RSS=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  TAG=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -o 'tag [a-zA-Z0-9_]*' | head -1)
  echo "pid=$P state=$ST rss=${RSS}kB $TAG"
done
echo "--- 负载 ---"
uptime
