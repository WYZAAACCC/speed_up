#!/usr/bin/env bash
# _r735_watch.sh —— 观察长 A/B 是否在推进（等待 240 s 再看落盘时间）。
set -uo pipefail
S=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_long/dry_L_off/series.csv
SNAP=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_long/dry_L_off
printf 'now        = %s\n' "$(date '+%H:%M:%S')"
printf 'series.csv = %s 行  mtime=%s\n' "$(wc -l < "$S")" "$(date -r "$S" '+%H:%M:%S')"
printf '快照最新   = %s\n' "$(ls -t "$SNAP"/snap_*.npz 2>/dev/null | head -1 | xargs -r basename)"
printf '等待 240 s ...\n'
sleep 240
printf '\n--- 240 s 后 ---\n'
printf 'now        = %s\n' "$(date '+%H:%M:%S')"
printf 'series.csv = %s 行  mtime=%s\n' "$(wc -l < "$S")" "$(date -r "$S" '+%H:%M:%S')"
printf '快照最新   = %s\n' "$(ls -t "$SNAP"/snap_*.npz 2>/dev/null | head -1 | xargs -r basename)"
printf '进程       = %s\n' "$(pgrep -a -f '[_]bk_exp.py' | cut -c1-60)"
printf '累计 CPU   = %s\n' "$(ps -o time= -p "$(pgrep -f '[_]bk_exp.py' | head -1)" 2>/dev/null | tr -d ' ')"
