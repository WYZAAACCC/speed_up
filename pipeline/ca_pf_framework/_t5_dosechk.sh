#!/bin/bash
# _t5_dosechk.sh --- 剂量臂是否有快照 + 监控是否在测它们
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 剂量臂的目录与快照 ════'
for t in t5AD_500 t5AD_700; do
  n=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)
  s=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | sort | tail -1 | sed 's/.*snap_//;s/\.npz//')
  printf '  %-10s 快照数=%-3s 最新=%s  末步=%s\n' "$t" "$n" "${s:-（无）}" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ ② 剂量臂日志末尾（看是否报错）════'
for t in t5AD_500 t5AD_700; do
  echo "  ── $t ──"
  tail -2 _w2_t5_ad_$t.log 2>/dev/null | cut -c1-120 | sed 's/^/     /'
done
echo
echo '════ ③ 监控日志里是否出现剂量臂 ════'
grep -c 't5AD_' _w2_t5_ar_monitor.log 2>/dev/null | sed 's/^/  含 t5AD_ 的行数 = /'
echo
echo '════ ④ 监控进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[p]ython _t5_armon' | cut -c1-60 | sed 's/^/  /'
