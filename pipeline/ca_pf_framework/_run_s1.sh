#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
/root/miniconda3/envs/ml/bin/python -u _chk_s1.py > _s1_reg.log 2>&1
/root/miniconda3/envs/ml/bin/python -u _chk_d4.py >> _s1_reg.log 2>&1
/root/miniconda3/envs/ml/bin/python -u _chk_w2.py >> _s1_reg.log 2>&1
/root/miniconda3/envs/ml/bin/python -u _chk_a3.py >> _s1_reg.log 2>&1
echo DONE >> _s1_reg.log
