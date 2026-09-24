#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
exec /root/miniconda3/envs/ml/bin/python -u windowB_rve3d.py \
    N=64 dx=2.0e-9 nstep=400 monitor=40 workers=8 dg_ratio=0.05 tag=_free
