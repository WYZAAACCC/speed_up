#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
for L in 0.0 0.90 0.99; do
  echo "########## lambda = $L ##########"
  $PY -u windowB_gibbs_rve.py N=32 dx=2.0e-8 nstep=60 monitor=60 nsel=1500 \
      k0=clamped df=5.0e8 aniso=$L tag=_L$L 2>&1 | grep -E '等效板条厚|S_v|回转半轴比|最近夹角|变体体积分数|max/min' 
done
