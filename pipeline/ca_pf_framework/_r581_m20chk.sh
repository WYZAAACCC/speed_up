#!/bin/bash
# _r581_m20chk.sh --- p2_m20 还活着吗？跑到哪了？（外加：现在整体状态）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 在跑的 _bk_exp 进程 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  pid=%-7s tag=%-10s state=%-3s RSS=%s MB\n' "$p" "${tag:-?}" "$st" "$rss"
done
echo '  （空 = 没有臂在跑）'
echo
echo '── p2_m20 的产物 ──'
found=0
for d in _exp/*/dry_p2_m20; do
  [ -d "$d" ] || continue
  found=1
  printf '  %s\n' "$d"
  printf '    step=%-8s 行=%-6s 快照=%s\n' \
    "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)" \
    "$(wc -l < "$d/series.csv" 2>/dev/null)" \
    "$(ls "$d" 2>/dev/null | grep -c '^snap_')"
  tail -2 "$d/series.csv" 2>/dev/null | cut -d, -f1,9,10,19,24 | sed 's/^/    /'
done
[ "$found" = "0" ] && echo '  （没有 dry_p2_m20 目录）'
echo
echo '── p2_m20 的日志尾 ──'
f=$(ls -t _w2_r581_*p2_m20*.log 2>/dev/null | head -1)
if [ -n "$f" ]; then
  echo "  $f"
  tail -4 "$f" | cut -c1-100 | sed 's/^/    /'
  printf '  Traceback=%s\n' "$(grep -c '^Traceback' "$f")"
else
  echo '  （没有日志）'
fi
echo
echo '── 队列脚本 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_(mqueue|mn64|p2q)' | grep -v grep | cut -c1-76
echo '  （空 = 没队列在跑）'
echo
echo '── 内存 ──'
free -m | sed -n 2,3p
