#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 扫描进度'
tail -6 _w2_r70_sweep_run.log 2>/dev/null
echo
echo '=== 各档的 f_flat 与 v_a/v_w'
printf '  %-6s %-10s %-12s %-12s %-10s %s\n' NP f_flat a 速率 w 速率 v_a/v_w 判定
for NP in 0 5 10 20 40 100; do
  d="_exp/_bk_mb/dry_fp$NP"
  [ -f "$d/series.csv" ] || { printf '  %-6s （无产物）\n' "$NP"; continue; }
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  [ "$n" -ge 300 ] || { printf '  %-6s （只到 %s 步）\n' "$NP" "$n"; continue; }
  ff=$(timeout 600 $PY _r65_corner.py "$d" 2>&1 | grep -oE '首末 f_flat: [0-9.]+ → [0-9.]+' | head -1)
  vv=$(timeout 600 $PY _r53_v2run.py "$d" 2>&1 | grep -E '^  全程' | head -1)
  printf '  %-6s %-10s %s\n' "$NP" "${ff##*→ }" "$vv"
done
