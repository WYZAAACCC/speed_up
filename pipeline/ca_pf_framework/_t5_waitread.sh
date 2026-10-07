#!/bin/bash
# _t5_waitread.sh --- 等到监控**真的出新轮**再读（把等待放进一次调用，第 23 条）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_ar_monitor.log
OLD=$(grep -c '  t5AD_700 +step ' "$L" 2>/dev/null || echo 0)
for i in $(seq 1 24); do          # 最多 24 × 30 s = 12 min
  sleep 30
  NEW=$(grep -c '  t5AD_700 +step ' "$L" 2>/dev/null || echo 0)
  [ "$NEW" -gt "$OLD" ] && break
done
echo "NOW = $(date '+%F %T')   （等到了新轮：$OLD → $NEW 条）"
echo '════ 剂量臂最新 ════'
grep -E '  t5AD_(500|700|1000) +step ' "$L" | sort -u | tail -3
echo '════ 对照/关键臂最新 ════'
grep -E '  t5AB_(A|B) +step ' "$L" | sort -u | tail -2
