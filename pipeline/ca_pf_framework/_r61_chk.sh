#!/bin/bash
# R61: 刻面验收三臂的进度与读数
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 运行日志尾'
tail -8 _w2_r61_accept_run.log 2>/dev/null
echo
echo '=== 各臂步数'
for t in wulff_c4 wulff_c0 wulff_off; do
  d="_exp/_bk_mb/dry_$t"
  if [ -f "$d/series.csv" ]; then
    printf '  %-12s step=%-6s snap=%s\n' "$t" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-12s （无产物）\n' "$t"
  fi
done
echo
echo '=== 完成的臂：v2 口径的 v_a/v_w'
for t in wulff_c4 wulff_c0 wulff_off; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || continue
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  [ "$n" -ge 300 ] || { echo "--- $t 只到 $n 步，跳过"; continue; }
  echo "--- $t"
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | tail -3
done
