#!/bin/bash
# _t5_mon2.sh --- 读第 2 轮完整六臂（去重，按臂排序）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 监控日志里所有"轮"标记 ════'
grep -n '第 .* 轮' _w2_t5_ar_monitor.log | tail -4 | sed 's/^/  /'
echo
echo '════ 每臂的**最新**一条读数（去重后取末条）════'
for t in t5AB_A t5AB_B t5AB_C t5AB_D t5V2 t5H3; do
  L=$(grep "  $t  " _w2_t5_ar_monitor.log | tail -1)
  [ -n "$L" ] && echo "  $L"
done
echo
echo '════ 长宽比/长厚比 的**时间序列**（每臂，只取数值）════'
for t in t5AB_A t5AB_B t5AB_C t5AB_D; do
  echo "  ── $t ──"
  grep "  $t  " _w2_t5_ar_monitor.log | sed 's/.*step \([0-9]*\).*长宽比 中位 \([0-9.]*\).*长厚比 中位 \([0-9.]*\).*/     step \1  →  长宽比 \2   长厚比 \3/' | tail -4
done
