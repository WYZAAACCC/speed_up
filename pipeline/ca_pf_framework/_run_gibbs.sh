#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=6
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
$PY -u windowB_gibbs_rve.py N=64 dx=1.0e-8 nstep=400 monitor=40 nsel=2000 \
    k0=free tag=_free64 > _gibbs_free64.log 2>&1
$PY -u windowB_gibbs_rve.py N=64 dx=1.0e-8 nstep=400 monitor=40 nsel=2000 \
    k0=clamped tag=_clamp64 > _gibbs_clamp64.log 2>&1
echo DONE > _gibbs_done.flag
