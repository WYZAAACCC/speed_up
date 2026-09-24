#!/bin/bash
# 修掉 allow_parent 后, 用中等 Lambda + 大晶核 看能否"既跑完转变又保持板条"
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
pkill -f 'windowB_gibbs_rve.py' 2>/dev/null
sleep 1
for spec in "10 _UF10" "6 _UF6"; do
  set -- $spec
  echo "########## Lambda=$1 ##########"
  $PY -u windowB_gibbs_rve.py N=48 dx=2.0e-8 nstep=400 monitor=50 nsel=2500 \
      k0=clamped df=1.0e9 aniso=$1 thick=2 nplate=1 rfrac=0.30 ntol=1e-6 tag=$2 2>&1 \
      | grep -E 'it +[0-9]+/|板片厚度|放置|回转半轴比|最近夹角|max/min'
done
echo DONE > _unfreeze_done.flag
