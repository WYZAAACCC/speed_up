#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/pf3g
timeout 1800 /root/projects/gibbs/gibbs-opt -i pf3grain_mercedes.i > run.log 2>&1
echo "rc=$?  JIT=$(grep -c 'JIT compile failed' run.log)  未收敛=$(grep -c 'Solve Did NOT Converge' run.log)"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A5 -m1 '\*\*\* ERROR' | head -8
echo "首行: $(sed -n 2p pf3grain_mercedes_out.csv)"
echo "末行: $(tail -1 pf3grain_mercedes_out.csv)"
echo "行数: $(wc -l < pf3grain_mercedes_out.csv)"
cp -f run.log pf3grain_mercedes.i pf3grain_mercedes_out.csv /mnt/f/speed_up/pipeline/gibbs/results_pf3g/ 2>/dev/null