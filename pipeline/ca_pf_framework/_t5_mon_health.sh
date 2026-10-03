#!/bin/bash
# _t5_mon_health.sh --- 监控健康检查（第 3 轮为何没来）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 监控与守护进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '[_]t5_armon|[_]t5_mon_keeper' \
  | cut -c1-72 | sed 's/^/  /'
echo
echo '════ ② 日志的**最后修改时间**（判断它是否还在写）════'
stat -c '  %n  最后写于 %y  大小 %s' _w2_t5_ar_monitor.log 2>/dev/null
stat -c '  %n  最后写于 %y  大小 %s' _w2_t5_mon_keeper.log 2>/dev/null
echo
echo '════ ③ 日志末尾 3 行（看停在哪）════'
tail -3 _w2_t5_ar_monitor.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ ④ 各臂当前步（判断是否只剩"构造期"而没新快照）════'
for t in t5AB_A t5AB_B t5AB_C t5AB_D t5V2; do
  printf '  %-9s 末步=%s\n' "$t" "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ ⑤ 守护日志 ════'
tail -6 _w2_t5_mon_keeper.log 2>/dev/null | sed 's/^/  /'
