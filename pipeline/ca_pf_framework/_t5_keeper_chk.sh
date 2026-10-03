#!/bin/bash
# _t5_keeper_chk.sh --- 核对五个监控/守护进程
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for p in _t5_armon _t5_blkmon _t5_milewatch _t5_keeper_all _t5_mon_keeper _t5_finalwatch2; do
  N=$(ps -eo args --no-headers 2>/dev/null | awk -v q="$p" 'index($0,q){n++} END{print n+0}')
  printf '  %-20s %s\n' "$p" "$N"
done
echo
printf '  t5N276 末步 = %s   引擎进程 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(ps -eo args --no-headers 2>/dev/null | awk '/--tag t5N276/{n++} END{print n+0}')"
echo
echo '── 守护日志 ──'
tail -3 _w2_t5_keeper_all.log 2>/dev/null | sed 's/^/  /'
