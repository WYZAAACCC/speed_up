#!/bin/bash
# _t5_alive.sh --- 极简存活核对（监控链条 + 各臂）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo -n '  监控 _t5_armon  : '; ps -eo args --no-headers | grep -c '[p]ython _t5_armon'
echo -n '  守护 _t5_mon_keeper: '; ps -eo args --no-headers | grep -c '[_]t5_mon_keeper'
echo -n '  引擎 bk_exp 进程数 : '; ps -eo args --no-headers | grep -c '[_]bk_exp.py'
echo '  ── 各臂末步 ──'
for t in t5AB_A t5AB_B t5AB_C t5AB_D t5AD_500 t5AD_700 t5AD_1000 t5V2; do
  printf '    %-11s %s\n' "$t" "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo '  ── 监控日志最后写入时间 ──'
stat -c '    %y  (%s 字节)' _w2_t5_ar_monitor.log 2>/dev/null
echo '  ── 内存 ──'
free -m | sed -n 2p | sed 's/^/    /'
