#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
/root/miniconda3/envs/ml/bin/python -u _chk_w1.py "$@" 2>&1 | grep -v Warning
