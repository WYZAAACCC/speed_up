#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 进度'
tail -6 _w2_r64_accept_run.log 2>/dev/null
echo
for t in ell3 ell9 ell20; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || { echo "$t 无产物"; continue; }
  n=$(tail -1 "$d/series.csv" | cut -d, -f1)
  echo "--- $t  步数=$n"
  [ "$n" -ge 300 ] || continue
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | tail -3
done
