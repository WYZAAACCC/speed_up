#!/bin/bash
# 第三批并行：T5→C4（Gibbs 吸附）的 A/B + 拖曳（线性 Cahn）的"钉扎量级"演示
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
BASE="STAGGER=1 AUTOSC=0 PRECOND=mumps NLATOL=1e-7 DTMAX=1e-8 WGB=8e-6 DX=2e-6 AMR=0"
gen() { suf=$1; shift; env $BASE OUTSUF="$suf" "$@" python3 make_gibbs3d.py > /dev/null 2>&1; ls -t *"$suf".i | head -1; }
F1=$(gen _t5A T5=1)
F2=$(gen _t5B T5=0)
F3=$(gen _dragOn DRAG=1 BETA=1e4 T5=1)
H=/mnt/f/speed_up/pipeline/gibbs/prod3d
cat > /tmp/batch3.list <<EOF
t5A|$H/$F1|Executioner/end_time=3e-7
t5B|$H/$F2|Executioner/end_time=3e-7
dragOn|$H/$F3|Executioner/end_time=3e-7
EOF
cat /tmp/batch3.list
