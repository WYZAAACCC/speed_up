#!/bin/bash
# _t5_sidefx2.sh --- ★★★ 副作用闸（**修提取 bug**：`%-8s` 补位导致 8 字符标签只跟 1 个空格）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 各臂"场数 vs step"（**用正则匹配标签**，不依赖空格数）════'
for t in t5AB_A t5AB_B t5AD_500 t5AD_700 t5AD_1000; do
  echo "  ── $t ──"
  grep -E "  $t +step " _w2_t5_ar_monitor.log | sort -u \
    | sed -E 's/.*step ([0-9]+) +场=([0-9]+).*长宽比 中位 ([0-9.]+).*/     step \1  场=\2  长宽比 \3/' \
    | tail -6
done
echo
echo '════ 同时刻场数对比（各臂**实际都有**的 step）════'
for s in 40 120 160 200 280 400; do
  printf '  step %-5s : ' "$s"
  for t in t5AB_A t5AB_B t5AD_500 t5AD_700 t5AD_1000; do
    v=$(grep -E "  $t +step $s +" _w2_t5_ar_monitor.log | sort -u | tail -1 \
        | sed -E 's/.*场=([0-9]+).*/\1/')
    printf '%-9s=%-4s ' "${t#t5}" "${v:-—}"
  done
  echo
done
