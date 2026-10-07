#!/bin/bash
# _r97_alive.sh —— R77/R76 是否还活着 + 进展速率
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(ps -eo args --no-headers | grep -c '[_]bk_exp.py')"
echo
echo "--- 进程明细（pid / 已运行秒 / CPU% / RSS MB）---"
ps -eo pid,etimes,pcpu,rss,args --no-headers | grep '[_]bk_exp.py' | \
  awk '{printf "  pid=%-8s %6ss  cpu=%-6s rss=%d MB  tag=%s\n", $1, $2, $3, $4/1024, $NF}'
echo
echo "--- 日志最近的 mtime 与末行 ---"
for f in _w2_r77_mo1fp10.log _w2_r77_mo1el0.log _w2_r77_mo2el0.log _w2_r30_regress.log; do
  [ -f "$f" ] || continue
  printf '  %-26s %s  %s B\n' "$f" "$(stat -c %y "$f" | cut -c1-19)" "$(stat -c %s "$f")"
done
echo
echo "--- 三个臂的最后一次读数 ---"
for t in mo1fp10 mo1el0 mo2el0; do
  printf -- '  %-9s %s\n' "$t" "$(grep 's/步' _w2_r77_${t}.log | tail -1 | cut -c1-110)"
done
echo
echo "--- R76 回归 ---"
ls -la --time-style='+%H:%M:%S' _exp/_bk_eng/dry_r30reg/series.csv 2>/dev/null
tail -3 _w2_r30_regress.log
