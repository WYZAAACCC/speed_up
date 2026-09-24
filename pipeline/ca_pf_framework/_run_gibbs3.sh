#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
exec /root/miniconda3/envs/ml/bin/python -u windowB_gibbs_rve.py \
    N=64 dx=1.0e-8 nstep=600 monitor=50 nsel=2500 k0=clamped df=5.0e8 tag=_globC
