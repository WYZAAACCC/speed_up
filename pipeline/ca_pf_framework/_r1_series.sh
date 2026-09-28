#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for d in "$@"; do
  echo "=== $d ==="
  timeout 1800 $PY -u _r1_snapinfo.py --series "_exp/$d" --kv 1 --shape "${SHAPE:-mid}" 2>&1 | tail -20
  echo
done
