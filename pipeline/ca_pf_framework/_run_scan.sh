#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1
exec /root/miniconda3/envs/ml/bin/python -u _scan_w90.py
