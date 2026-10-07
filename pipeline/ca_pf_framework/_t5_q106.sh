#!/bin/bash
# _t5_q106.sh --- 三臂进度（快照口径）+ 等待作业日志
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5FIX t5ETAo t5BKMo; do
  S=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | sed 's/.*snap_//; s/\.npz//' | sort -n | tail -1)
  N=$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)
  P=$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- "--tag $t")
  printf '  %-8s 最大快照=%-7s 快照数=%-3s 进程=%s ｜ 日志 %s\n' \
    "$t" "${S:-无}" "$N" "$([ "$P" -gt 0 ] && echo 在 || echo 停)" \
    "$(stat -c '%y' _w2_t5_short_$t.log 2>/dev/null | cut -c12-19)"
done
echo
echo '════ 等待作业日志（到 640 会自动出四项比较）════'
tail -8 _w2_t5_waitfix.log 2>/dev/null | sed 's/^/  /'
echo
echo '════ 等待作业是否在跑 ════'
ps -eo args --no-headers 2>/dev/null | grep -c '[_]t5_waitfix.sh' | sed 's/^/  waitfix 进程数 = /'
free -m | sed -n 2p | sed 's/^/  /'
