#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY -u _r1_partest.py --mode scale --N 192 --th 16 --reps 2 > _w2_r1scale192.log 2>&1
echo "rc=$?"
