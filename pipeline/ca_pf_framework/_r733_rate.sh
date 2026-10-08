#!/usr/bin/env bash
# _r733_rate.sh —— 从运行日志估**真实步速**（判长 A/B 值不值得跑完）。
set -uo pipefail
LOG=/mnt/f/speed_up/_w2_longab.log
echo "=== 进程存活 ==="
pgrep -a -f '[_]bk_exp.py' | cut -c1-90 || echo "  （无）"
echo
echo "=== 日志里已出现的测点行数与末行 s/步 ==="
grep -o '\[ *[0-9]*\].*s/步' "$LOG" 2>/dev/null | tail -4
echo
echo "=== series.csv 行数与 mtime ==="
for t in L_off L_on; do
  f=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_long/dry_$t/series.csv
  if [ -f "$f" ]; then
    echo "  $t: $(wc -l < "$f") 行  mtime=$(date -r "$f" '+%H:%M:%S')"
  else
    echo "  $t: 尚无"
  fi
done
echo
echo "=== 日志 mtime 与当前时间 ==="
echo "  log mtime = $(date -r "$LOG" '+%H:%M:%S')   now = $(date '+%H:%M:%S')"
