#!/bin/bash
# _t5_q104.sh --- 快照口径的进度 + 三臂步对齐
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
for t in t5FIX t5ETAo t5BKMo; do
  SNAP=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | sed 's/.*snap_//; s/\.npz//' | sort -n | tail -1)
  N=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)
  P=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- "--tag $t")
  printf '  %-8s **最大快照=%-7s** 快照数=%-3s 进程=%s ｜ 日志最后写 %s\n' \
    "$t" "${SNAP:-无}" "$N" "$([ "$P" -gt 0 ] && echo 在 || echo 停)" \
    "$(stat -c '%y' _w2_t5_short_$t.log 2>/dev/null | cut -c12-19)"
done
echo
echo '════ ★★ 三臂步对齐（同一 step）════'
timeout 1500 $PY _t5_aralign.py 400,480,560 2>&1 | sed -n '4,8p'
echo
echo '════ ★ 每档核数（burst 生效判据）════'
for t in t5FIX t5ETAo t5BKMo t5N276F; do
  printf '  [%-8s] %s\n' "$t" "$(grep -oE 'T=[0-9.]+ K' _w2_t5_short_$t.log 2>/dev/null | sort | uniq -c | head -4 | tr '\n' ' ')"
done
free -m | sed -n 2p | sed 's/^/  /'
