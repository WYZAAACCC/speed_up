#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== cln11 是否跑完'
tail -3 _w2_bk_cln11.log 2>/dev/null
echo -n '  进程: '; ps -eo pid,args --no-headers | grep -F 'cln11' | grep -v grep | wc -l
echo
echo '=== 各臂进度'
for d in _exp/_bk_mb/dry_mb1L _exp/_bk_mb/dry_mb1Ls _exp/_bk_mb/dry_mb1s62 _exp/_bk_closed/dry_cln11; do
  st=$(tail -1 "$d/series.csv" | cut -d, -f1)
  nn=$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)
  printf '  %-28s step=%-6s snap=%s\n' "$d" "$st" "$nn"
done
echo
echo '=== 进程/负载'
ps -eo pcpu,rss,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "  %5s%% %5dMB %6ss %s\n",$1,$2/1024,$3,$4}'
uptime; free -g | head -2
