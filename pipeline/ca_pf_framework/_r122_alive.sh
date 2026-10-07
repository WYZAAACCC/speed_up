#!/bin/bash
# _r122_alive.sh —— 当前在跑什么
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
N=$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)
echo "_bk_exp 进程数：$N"
ps -eo pid,etimes,rss,args --no-headers | grep '[_]bk_exp' | \
  awk '{printf "  pid=%-7s %5ss  rss=%6.0f MB  tag=%s\n", $1, $2, $3/1024, $NF}'
free -g | awk 'NR==2{printf "内存：%s GB available\n", $7}'
echo
echo "--- R115（保面对照）---"
tail -2 _w2_r115_run.log 2>/dev/null || echo "  （无日志）"
echo
echo "--- R120（双判据扫描）---"
tail -8 _w2_r120_run.log 2>/dev/null || echo "  （无日志）"
echo
echo "--- 已完成的扫描臂 ---"
for t in t1N96L800 t1N96L1000 t1N112L1000 t1N112L800 t2N128L1600 t2N128L1200 t3N128L1000 t3N112L1200; do
  [ -f "_exp/_bk_mb/dry_$t/meta.json" ] && printf '  %-13s ✅\n' "$t"
done
