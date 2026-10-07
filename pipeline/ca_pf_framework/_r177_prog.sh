#!/bin/bash
# _r177_prog.sh —— 只打 R165 两臂的进度行（末 2 行）。不杀、不改。
cd "$(dirname "$0")" || exit 1
for d in dry_saSet2F2 dry_saOddGF2; do
  f="_exp/_bk_mb/$d/series.csv"
  if [ -f "$f" ]; then
    printf '%-14s rows=%-4s ' "$d" "$(wc -l < "$f")"
    tail -1 "$f" | cut -d, -f1-2 | tr '\n' ' '
    echo
  else
    printf '%-14s (无 series.csv)\n' "$d"
  fi
done
echo "--- 进程 ---"
ps -eo pid,etime,pcpu,rss,args 2>/dev/null | grep -F '_bk_exp.py' | grep -v grep | wc -l
echo "--- 内存(MB) ---"
free -m | head -2
