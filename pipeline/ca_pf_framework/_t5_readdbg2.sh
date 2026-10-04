#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%H:%M:%S') ==="
for T in t5FIX t5BKMo t5ETAo; do
  echo "════ $T ════"
  grep -a 's295 形核分诊' _w2_t5_short_$T.log 2>/dev/null | tail -3
  echo "    事件=$(grep -ac '块内第' _w2_t5_short_$T.log 2>/dev/null) fresh拒=$(grep -ac 'fresh` 被拒' _w2_t5_short_$T.log 2>/dev/null)"
done
echo
echo "=== dbg 字段逐个拆开（看有没有 sites_resampled / fresh_exc）==="
for T in t5FIX t5BKMo t5ETAo; do
  echo "--- $T ---"
  grep -a 's295 形核分诊' _w2_t5_short_$T.log 2>/dev/null | tail -1 \
    | tr ' ' '\n' | grep '=' | sed 's/^/     /'
done
