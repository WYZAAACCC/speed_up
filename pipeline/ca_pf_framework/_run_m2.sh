#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=6
export PYTHONDONTWRITEBYTECODE=1
/root/miniconda3/envs/ml/bin/python -u _chk_m2.py "$@" > _m2_out.log 2>&1
echo DONE >> _m2_out.log
