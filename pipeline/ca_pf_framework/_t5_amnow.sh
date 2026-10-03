#!/bin/bash
# _t5_amnow.sh --- 两臂当前状态（存活 / step / traceback / 快照）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep t5AM | cut -c1-62 | sed 's/^/  /'
echo -n '  t5AM 进程数 = '; ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c t5AM
echo
echo '════ 各自日志：最后 step 行 / Traceback / 最后修改 ════'
for t in t5AM_ell t5AM_combo; do
  L=_w2_t5_short_$t.log
  printf '  ── %s ──\n' "$t"
  printf '     最后 step 行 = %s\n' "$(grep -oE '^\[ *[0-9]+\]' "$L" 2>/dev/null | tail -1)"
  printf '     Traceback 次数 = %s\n' "$(grep -c Traceback "$L" 2>/dev/null)"
  printf '     日志最后修改 = %s\n' "$(stat -c%y "$L" 2>/dev/null | cut -d. -f1)"
  printf '     末步 = %s   快照数 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo '════ 对照：正常臂的日志最后修改（应都是"刚刚"）════'
for t in t5AB_A t5AD_700; do
  printf '  %-12s %s\n' "$t" "$(stat -c%y _w2_t5_short_$t.log 2>/dev/null | cut -d. -f1)"
done
