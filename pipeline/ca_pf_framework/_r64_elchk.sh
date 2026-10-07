#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 弹性缩放实验的读数（v2 口径）'
for t in el0 el05 el1; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || { echo "$t 无产物"; continue; }
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  printf -- '--- %-6s 步数=%s\n' "$t" "$n"
  [ "$n" -ge 300 ] || continue
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | tail -3
done
