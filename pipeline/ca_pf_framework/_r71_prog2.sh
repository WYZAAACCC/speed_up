#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== R71 进程'
ps -eo pid,pcpu,rss,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-95
echo
echo '=== m3fp10 日志尾'
tail -4 _w2_r71_m3fp10.log 2>/dev/null | cut -c1-140
echo
echo '=== m3fp0 日志尾'
tail -4 _w2_r71_m3fp0.log 2>/dev/null | cut -c1-140
echo
echo "  现在: $(date '+%F %T')"
ls -d _exp/_bk_mb/dry_m3fp10 _exp/_bk_mb/dry_m3fp0 2>/dev/null
