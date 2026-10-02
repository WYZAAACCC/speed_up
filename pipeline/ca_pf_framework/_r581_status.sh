#!/bin/bash
# _r581_status.sh --- 一行看状态：跑着的算例 + 最新日志尾巴 + 资源
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T')  uptime:$(uptime | sed 's/.*load average/load/') ==="
free -m | sed -n '2p'
echo "--- python/_bk_exp 进程 ---"
ps -eo pid,etime,pcpu,rss,args --no-headers 2>/dev/null | grep -E '_bk_exp|_r581|_r57[0-9]' | grep -v grep || echo "  (无)"
echo "--- _w2_r581_*.log（按时间倒序，最多 6 个）---"
ls -t _w2_r581_*.log 2>/dev/null | head -6 | while read -r f; do
  printf '  %-34s %s\n' "$f" "$(tail -1 "$f" 2>/dev/null | cut -c1-110)"
done
