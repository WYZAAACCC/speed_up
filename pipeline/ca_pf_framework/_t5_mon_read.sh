#!/bin/bash
# _t5_mon_read.sh --- 读监控日志（去重）+ 各臂进度
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 监控日志（最后 2 轮，已去重）════'
tail -30 _w2_t5_ar_monitor.log 2>/dev/null | awk '!seen[$0]++' | tail -14 | sed 's/^/  /'
echo
echo '════ ② 四臂 A/B 的当前步 ════'
for t in A B C D; do
  printf '  t5AB_%-2s 末步=%-6s 行数=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_t5AB_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(wc -l < _exp/_bk_t5/dry_t5AB_$t/series.csv 2>/dev/null)"
done
echo
echo '════ ③ 还在跑的长臂 t5V2 ════'
printf '  末步=%s  行数=%s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5V2/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(wc -l < _exp/_bk_t5/dry_t5V2/series.csv 2>/dev/null)"
echo
echo '════ ④ 进程（监控 + 四臂 + t5V2）════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '[_]t5_armon|[_]bk_exp.py|[_]t5_ab_elong' \
  | sed 's/^/  /' | cut -c1-88
echo
free -m | sed -n 2p | sed 's/^/  内存: /'
