#!/bin/bash
# R57: 查 E-1（平流格式对照）的进度与结果
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== E-1 运行日志尾'
tail -8 _w2_r57_adv_run.log 2>/dev/null
echo
echo '=== 各臂进度'
for t in adv_proj2 adv_upwind adv_central; do
  d="_exp/_bk_mb/dry_$t"
  if [ -f "$d/series.csv" ]; then
    printf '  %-14s step=%-6s snap=%s\n' "$t" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-14s （无产物）\n' "$t"
  fi
done
echo
echo '=== 完成的臂直接量 v_a/v_w（v2 口径）'
for t in adv_proj2 adv_upwind adv_central; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || continue
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  [ "$n" -ge 300 ] || { echo "--- $t 只到 $n 步，跳过"; continue; }
  echo "--- $t"
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | tail -4
done
