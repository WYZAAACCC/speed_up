#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=6
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
for spec in "5.0e8 df5e8" "2.0e8 df2e8" "5.0e7 df5e7long"; do
  set -- $spec
  $PY -u windowB_gibbs_rve.py N=64 dx=1.0e-8 nstep=900 monitor=100 nsel=2500 \
      k0=free df=$1 tag=_$2 > _gibbs_$2.log 2>&1
done
echo DONE > _gibbs2_done.flag
