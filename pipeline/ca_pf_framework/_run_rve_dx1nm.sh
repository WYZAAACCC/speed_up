#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=10
exec /root/miniconda3/envs/ml/bin/python windowB_rve3d.py \
    N=128 dx=1.0e-9 nstep=500 monitor=50 workers=10 dg_ratio=0.05 tag=_dx1nm
