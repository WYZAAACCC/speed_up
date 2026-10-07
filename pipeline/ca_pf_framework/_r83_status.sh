#!/bin/bash
# _r83_status.sh —— 回归 + R77 隔离臂的状态一屏看完
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 现在 $(date '+%F %T')"
echo "=== _bk_exp 进程数：$(ps -eo args --no-headers | grep -c '[_]bk_exp.py')"
echo
echo "=== ① R76 回归（schema 改动后）"
tail -14 _w2_r30_regress.log 2>/dev/null
echo
echo "=== ② R77 隔离臂"
tail -3 _w2_r77_run.log 2>/dev/null
for t in mo1fp10 mo2el0 mo1el0; do
  L="_w2_r77_${t}.log"
  if [ -f "$L" ]; then
    printf -- '--- %-9s %s\n' "$t" "$(grep -c . "$L") 行"
    tail -2 "$L"
  else
    printf -- '--- %-9s （日志未出现）\n' "$t"
  fi
done
echo
echo "=== ③ 数据目录"
for t in dry_mb2fp10 dry_mb2fp0 dry_mo1fp10 dry_mo2el0 dry_mo1el0; do
  d="_exp/_bk_mb/$t"
  if [ -d "$d" ]; then
    n=$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)
    printf -- '  %-16s 快照 %-4s  %s\n' "$t" "$n" "$(ls -la "$d/series.csv" 2>/dev/null | awk '{print $5" B  "$6" "$7" "$8}')"
  else
    printf -- '  %-16s （无）\n' "$t"
  fi
done
