#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 回归臂是否在跑'
ps -eo pid,pcpu,etimes,args --no-headers | grep -F 'r30reg' | grep -v grep | cut -c1-100
echo '=== 回归产物'
ls -la _exp/_bk_eng/dry_r30reg/ 2>/dev/null | head -8
[ -f _exp/_bk_eng/dry_r30reg/series.csv ] && echo "行数=$(wc -l < _exp/_bk_eng/dry_r30reg/series.csv)"
echo
echo '=== 所有长跑进度'
for d in _exp/_bk_mb/dry_mb1L _exp/_bk_mb/dry_mb1Ls _exp/_bk_mb/dry_mb1s62 _exp/_bk_closed/dry_cln11; do
  [ -f "$d/series.csv" ] && printf '%-28s step=%-6s rows=%-4s snap=%s\n' "$d" \
    "$(tail -1 $d/series.csv | cut -d, -f1)" "$(wc -l < $d/series.csv)" "$(ls $d/snap_*.npz 2>/dev/null | wc -l)"
done
echo
ps -eo pcpu,rss,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "%5s%% %6dMB %6ss\n",$1,$2/1024,$3}'
free -g | head -2; uptime
