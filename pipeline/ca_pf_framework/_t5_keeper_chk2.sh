#!/bin/bash
# _t5_keeper_chk2.sh --- 干净的进程计数（**排除计数工具自身**，P27）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 只数 **python 进程**（避免 awk/grep 自匹配）════'
# 先把进程表存进变量，再用 bash 内建匹配 ⇒ 计数工具不进表
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_finalwatch2.py; do
  N=$(printf '%s\n' "$SNAP" | grep -c "python .*$p")
  printf '  %-22s %s\n' "$p" "$N"
done
for p in _t5_keeper_all.sh _t5_mon_keeper.sh; do
  N=$(printf '%s\n' "$SNAP" | grep -c "bash $p")
  printf '  %-22s %s\n' "$p" "$N"
done
echo
echo '════ 引擎（t5N276 及其它）════'
printf '  t5N276 引擎 = %s   全部引擎 = %s\n' \
  "$(printf '%s\n' "$SNAP" | grep -c 'bk_exp.py.*--tag t5N276')" \
  "$(printf '%s\n' "$SNAP" | grep -c '[_]bk_exp.py')"
printf '  t5N276 末步 = %s\n' "$(tail -1 _exp/_bk_t5/dry_t5N276/series.csv 2>/dev/null | cut -d, -f1)"
echo
echo '════ ★ 判据（P27）：若上面每个都是 1，则"2"确实是计数工具自匹配 ⇒ 进程正常 ════'
