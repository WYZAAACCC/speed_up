#!/bin/bash
# _t5_amwait.sh --- 等 t5AM_* 出现 **step ≥ 40** 的读数再打印（回答"公式给出多少各向异性"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_ar_monitor.log
OLD=$(grep -cE '  t5AM_ell +step ' "$L" 2>/dev/null || echo 0)
for i in $(seq 1 40); do          # 最多 40 × 30 s = 20 min
  S=$(tail -1 _exp/_bk_t5/dry_t5AM_ell/series.csv 2>/dev/null | cut -d, -f1)
  if [ -n "$S" ] && [ "$S" -ge 40 ] 2>/dev/null; then
    # 等到监控把它测出来
    N=$(grep -cE '  t5AM_ell +step ' "$L" 2>/dev/null || echo 0)
    [ "$N" -gt "$OLD" ] && break
  fi
  A=$(ps -eo args --no-headers 2>/dev/null | grep -c 'dry_t5AM_ell')
  [ "$A" -eq 0 ] && { echo "⚠ t5AM_ell 进程消失（可能又死）"; break; }
  sleep 30
done
echo "NOW = $(date '+%F %T')"
echo '════ ★ 迁移率臂（ellipse）vs 对照（exp2）════'
grep -E '  t5AM_(ell|combo) +step |  t5AB_A +step |  t5AD_700 +step ' "$L" 2>/dev/null | sort -u | tail -6
echo
echo '════ 末步 ════'
for t in t5AM_ell t5AM_combo; do
  printf '  %-12s 末步=%-6s 进程=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t")"
done
