#!/bin/bash
# μ 探针：T5 开 / 关，各带 mu_probe（导出 mu 属性场 + 全场极值）
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
BASE="STAGGER=1 AUTOSC=0 PRECOND=mumps NLATOL=1e-7 DTMAX=1e-8 WGB=8e-6 DX=2e-6 AMR=0 MU_PROBE=1"
H=/mnt/f/speed_up/pipeline/gibbs/prod3d
env $BASE T5=1 OUTSUF=_mpA python3 make_gibbs3d.py > /dev/null 2>&1
env $BASE T5=0 OUTSUF=_mpB python3 make_gibbs3d.py > /dev/null 2>&1
env $BASE T5=1 T5_MULT=100 OUTSUF=_mpC python3 make_gibbs3d.py > /dev/null 2>&1
cat > /tmp/batch4.list <<EOF
mpA|$H/$(ls -t *_mpA.i | head -1)|Executioner/end_time=2e-8
mpB|$H/$(ls -t *_mpB.i | head -1)|Executioner/end_time=2e-8
mpC|$H/$(ls -t *_mpC.i | head -1)|Executioner/end_time=2e-8
EOF
cat /tmp/batch4.list
