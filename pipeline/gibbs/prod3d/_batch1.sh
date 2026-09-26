#!/bin/bash
# 第一批并行作业（数值 1/2/3 + 基线）：一次生成 4 个输入，然后并行跑
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
BASE="STAGGER=1 AUTOSC=0 PRECOND=mumps NLATOL=1e-7 WGB=8e-6 DX=2e-6"
echo "== 生成 4 个输入 =="
env $BASE AMR=0 DTMAX=1e-7 OUTSUF=_amr   python3 make_gibbs3d.py > /dev/null 2>&1   # 先占位（下面再用 AMR=1 覆盖）
env $BASE AMR=1 DTMAX=1e-7 OUTSUF=_amr   python3 make_gibbs3d.py > /dev/null 2>&1
env $BASE AMR=0 DTMAX=1e-8 OUTSUF=_dt01  python3 make_gibbs3d.py > /dev/null 2>&1
env $BASE AMR=0 DTMAX=1e-7 DIM2=1 OUTSUF=_2d python3 make_gibbs3d.py > /dev/null 2>&1
env $BASE AMR=0 DTMAX=1e-7 TISO=1800 GAMIC=0 DISP=1 OUTSUF=_iso3d python3 make_gibbs3d.py > /dev/null 2>&1
ls -la stage1_meltpool_gibbs3d_*_*.i | awk '{print $9, $5}'
HERE=/mnt/f/speed_up/pipeline/gibbs/prod3d
cat > /tmp/batch1.list <<EOF
amr|$HERE/stage1_meltpool_gibbs3d_amr.i|Executioner/end_time=3e-7
dt01|$HERE/stage1_meltpool_gibbs3d_dt01.i|Executioner/end_time=3e-7
m2d|$HERE/stage1_meltpool_gibbs3d_2d.i|Executioner/end_time=3e-7
iso3d|$HERE/stage1_meltpool_gibbs3d_iso3d.i|Executioner/end_time=3e-7 UserObjects/gb_stagger/k_att=0
EOF
cat /tmp/batch1.list
