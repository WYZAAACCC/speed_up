#!/bin/bash
# 区分"晶核被冻住"的三种成因: 扫 Lambda(各向异性强度) 与 晶核厚度
# 观测量: 母相分数随时间 (能不能长大) + 板片厚度 t=2f/S_v
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
pkill -f 'windowB_gibbs_rve.py' 2>/dev/null
sleep 1
run () {  # $1=Lambda  $2=thick  $3=tag
  echo "########## Lambda=$1 thick=$2 ##########"
  $PY -u windowB_gibbs_rve.py N=32 dx=2.0e-8 nstep=250 monitor=50 nsel=2000 \
      k0=clamped df=8.0e8 aniso=$1 thick=$2 nplate=1 rfrac=0.18 ntol=1e-6 tag=$3 2>&1 \
      | grep -E 'it +[0-9]+/|板片厚度|放置'
}
run 2  2 _L2
run 5  2 _L5
run 20 6 _L20t6
echo DONE > _freeze_done.flag
