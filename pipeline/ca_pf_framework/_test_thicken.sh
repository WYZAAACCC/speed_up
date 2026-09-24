#!/bin/bash
# "板条能否变厚" 的决定性实验: 允许能量中性移动(ntol>0) 后, 厚度 t=2f/S_v 是否随时间增长?
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
PY=/root/miniconda3/envs/ml/bin/python
pkill -f 'windowB_gibbs_rve.py' 2>/dev/null
sleep 1
$PY -u windowB_gibbs_rve.py N=32 dx=2.0e-8 nstep=400 monitor=50 nsel=2000 \
    k0=clamped df=8.0e8 aniso=20 nplate=1 rfrac=0.18 ntol=1e-6 tag=_thick 2>&1 \
    | grep -E 'it |板片厚度|S_v|回转半轴比|最近夹角|母相'
