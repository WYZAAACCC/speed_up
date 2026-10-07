#!/usr/bin/env bash
# _r403_blocks6.sh -- 两个臂都出"6 块特写"
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for A in saSet2P0 saSet2; do
  echo "################ $A"
  $PY -u _r402_blocks6.py --arm "$A" 2>&1 | tail -3
done
echo
ls -l --time-style=+%H:%M _viz/
