#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%H:%M:%S') ==="
for T in t5FIX t5BKMo t5ETAo; do
  L=_w2_t5_short_$T.log
  echo "--- $T ---"
  grep -a 's295 形核分诊' $L 2>/dev/null | tail -5 | cut -c1-230
  echo "    事件=$(grep -ac '块内第' $L 2>/dev/null) fresh拒=$(grep -ac 'fresh` 被拒' $L 2>/dev/null) 补投轮=$(grep -ac '◆ s292' $L 2>/dev/null)"
done
echo
echo "=== 若 dbg 为空，看构造横幅是否有 s293/s295 ==="
grep -aE '平行建块|s295' _w2_t5_short_t5ETAo.log | head -3 | cut -c1-200
echo
echo "=== 快照与节拍 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  echo "  $T n=$(ls $D/snap_*.npz 2>/dev/null|wc -l) 节拍=$(grep -aoE '[0-9.]+s/步' _w2_t5_short_$T.log 2>/dev/null | tail -1)"
done
