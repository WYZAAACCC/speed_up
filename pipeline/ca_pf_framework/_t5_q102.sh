#!/bin/bash
# _t5_q102.sh --- ★ 用 `wc -l` + 快照名重读真实进度（避 9p 陈旧读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5FIX t5ETAo t5BKMo; do
  S=_exp/_bk_t5/dry_$t/series.csv
  P=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- "--tag $t")
  L=$([ -f "$S" ] && wc -l < "$S" || echo 0)
  # 快照文件名是可靠的时间戳（文件名不会变，9p 也一致）
  SNAP=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | sed 's/.*snap_//; s/\.npz//' | sort -n | tail -1)
  LAST=$(awk -F, 'NR>1{s=$1} END{print s}' "$S" 2>/dev/null)
  printf '  %-8s series行=%-6s awk末步=%-7s **最大快照step=%-7s** 进程=%s\n' \
    "$t" "$L" "${LAST:-?}" "${SNAP:-无}" "$([ "$P" -gt 0 ] && echo 在 || echo 停)"
  echo "     日志最后写：$(stat -c '%y' _w2_t5_short_$t.log 2>/dev/null | cut -c1-19)"
done
echo
echo '════ ★ Vt 轨迹（从日志读，口径与引擎一致）════'
for t in t5FIX t5ETAo t5BKMo; do
  echo "  [$t] $(grep -oE '^ *\[ *[0-9]+\] Vt=[0-9.]+' _w2_t5_short_$t.log 2>/dev/null | tail -5 | tr '\n' ' ')"
done
echo
echo '════ ★ 每档核数（burst 是否生效）════'
for t in t5FIX t5ETAo t5BKMo; do
  echo "  [$t] $(grep -oE 'T=[0-9.]+ K' _w2_t5_short_$t.log 2>/dev/null | sort | uniq -c | head -4 | tr '\n' ' ')"
done
free -m | sed -n 2p | sed 's/^/  /'
