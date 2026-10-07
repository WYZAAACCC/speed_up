#!/usr/bin/env bash
# _r401_viz2.sh -- 两臂都出图
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for A in saSet2P0 saSet2; do
  echo "################ $A"
  timeout 1800 $PY -u _r400_viz.py --arm "$A" --nsteps 8 2>&1 | tail -6
done
echo
echo "=== 产物 ==="
ls -l --time-style=+%H:%M _viz/ 2>&1 | head -12
