#!/bin/bash
# _t5_nslab.sh --- 各臂当前的**板条数** `nslab_n`（含 t5N276 的容量上限对照）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 各在跑臂的板条数（series.csv 末行的 nslab_n）════'
printf '  %-12s %-8s %-9s %-10s %-11s %s\n' '臂' '末步' 'nslab_n' 'nf3_col' 'Vt(µm³)' 'nv(容量)'
for t in t5N276 t5V2 t5AB_A t5AD_700 t5AD_1000 t5AM_ell t5AM_combo t5H3; do
  L=_exp/_bk_t5/dry_$t/series.csv
  [ -f "$L" ] || continue
  LAST=$(tail -1 "$L")
  ST=$(echo "$LAST" | cut -d, -f1)
  NS=$(echo "$LAST" | awk -F, '{print $9}')       # nslab_n 是第 9 列
  NF=$(echo "$LAST" | awk -F, '{print $10}')      # nf3_col 第 10 列
  VT=$(echo "$LAST" | awk -F, '{print $6*1e18}')  # Vt 第 6 列（m³→µm³）
  NV=$(grep -m1 -oE 'nv=[0-9]+' _w2_t5_n276.log _w2_t5_short_$t.log _w2_t5_am_$t.log _w2_t5_ad_$t.log 2>/dev/null \
       | grep -oE '[0-9]+' | head -1)
  printf '  %-12s %-8s %-9s %-10s %-11.4f %s\n' "$t" "${ST:-—}" "${NS:-—}" "${NF:-—}" "${VT:-0}" "${NV:-—}"
done
echo
echo '════ ★ t5N276 的容量对照（用户问"一共多少根"）════'
grep -E '总根数|导出板条数|B_max|几何上界' _w2_t5_n276.log 2>/dev/null | head -4 | sed 's/^/  /'
