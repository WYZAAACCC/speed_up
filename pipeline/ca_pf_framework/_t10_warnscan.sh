#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for L in _w2_t5_short_t10PRT2_b3_1005_1213.log _w2_t5_short_t10B9.log; do
  [ -f "$L" ] || continue
  echo "════════ $L ════════"
  echo "── 所有告警类行（⚠ / 不满足 / 失败 / 缺 / 越界 / 超 / 警告 / WARN / 兜底 / 退回）──"
  grep -anE '⚠|不满足|失败|越界|警告|WARN|兜底|退回|退化|INCONCLUSIVE|✗' "$L" 2>/dev/null \
    | head -40 | tr -d '\r' | cut -c1-170 | sed 's/^/  /'
  echo
  echo "── 告警行总数 = $(grep -acE '⚠|不满足|失败|越界|警告|WARN|兜底|退回|退化|INCONCLUSIVE' "$L" 2>/dev/null) ──"
  echo
done
echo "════════ 判据/自检类汇总（C-1..C-5 / V-x / P-x）════════"
for L in _w2_t5_short_t10PRT2_b3_1005_1213.log _w2_t5_short_t10B9.log; do
  [ -f "$L" ] || continue
  echo "── $L ──"
  grep -aoE '(✅|⚠|❌)? ?\*{0,4}C-[0-9][^|]{0,120}' "$L" 2>/dev/null | sort -u | head -14 | tr -d '\r' | sed 's/^/  /'
done
