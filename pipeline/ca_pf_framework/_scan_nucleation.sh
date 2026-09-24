#!/bin/bash
# 成核密度扫描: 板条厚应随成核密度上升而变薄（这是实验上可对照的量）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
pkill -f 'windowB_gibbs_rve.py' 2>/dev/null
sleep 1
for NP in 1 6; do
  echo "########## nplate = $NP ##########"
  $PY -u windowB_gibbs_rve.py N=32 dx=2.0e-8 nstep=150 monitor=150 nsel=1500 \
      k0=clamped df=8.0e8 aniso=20 nplate=$NP rfrac=0.18 tag=_N$NP 2>&1 \
      | grep -E '放置|等效板条厚|S_v|回转半轴比|最近夹角|母相分数|max/min|E_tot'
done
echo DONE > _gibbs_nucl_done.flag
