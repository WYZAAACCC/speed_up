#!/bin/bash
# _t5_sidefx.sh --- ★★★ 副作用闸：更扁的核是否让**场数**减少（= 更难长大）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 各臂"场数 vs step"（监控日志里已有）════'
for t in t5AB_A t5AB_B t5AD_500 t5AD_700 t5AD_1000; do
  echo "  ── $t ──"
  grep "  $t  " _w2_t5_ar_monitor.log | sort -u \
    | sed 's/.*step \([0-9]*\).*场=\([0-9]*\).*长宽比 中位 \([0-9.]*\).*/     step \1  场=\2  长宽比 \3/' \
    | tail -5
done
echo
echo '════ 同时刻的场数对比（找各臂共有的 step）════'
for s in 0 40 120 160 200 280 400; do
  printf '  step %-5s : ' "$s"
  for t in t5AB_A t5AB_B t5AD_500 t5AD_700 t5AD_1000; do
    v=$(grep "  $t  " _w2_t5_ar_monitor.log | grep "step $s " | sort -u | tail -1 \
        | sed 's/.*场=\([0-9]*\).*/\1/')
    printf '%-9s=%s  ' "${t#t5}" "${v:-—}"
  done
  echo
done
echo
echo '  ── 判读（预先写死）──'
echo '  若各臂**同时刻的场数相近** ⇒ 更扁的核**不减慢**形核（副作用闸通过）；'
echo '  若高剂量臂的场数**明显更少** ⇒ 更扁的核**更难长大**（须记账，并影响选值）。'
