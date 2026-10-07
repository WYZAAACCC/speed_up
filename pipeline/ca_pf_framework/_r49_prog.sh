#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== mb1s62 v3 进度'
tail -2 _w2_r49_mb1s62c.log 2>/dev/null
ls _exp/_bk_mb/dry_mb1s62/ 2>/dev/null | tail -4
echo
echo '=== 核心列是否已在 mb1s62 v3 落盘（关键：它决定第 ③ 步能不能立项）'
head -1 _exp/_bk_mb/dry_mb1s62/series.csv 2>/dev/null | tr ',' '\n' | grep -nE 'v_tip|v_side|dG_tip_p90|box_touch_core|tip_sep'
echo
echo '=== 各长跑进度'
for d in dry_mb1L dry_mb1Ls; do
  printf '%-11s ' "$d"
  tail -1 _exp/_bk_mb/$d/series.csv | cut -d, -f1
done
printf '%-11s ' dry_cln11; tail -1 _exp/_bk_closed/dry_cln11/series.csv | cut -d, -f1
echo
echo '=== 进程'
ps -eo pid,pcpu,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "%s %s%% %ss %s %s %s %s\n",$1,$2,$3,$8,$9,$10,$11}'
echo '=== load / mem'; uptime; free -g | head -2
