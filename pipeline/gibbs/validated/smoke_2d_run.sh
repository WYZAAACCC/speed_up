#!/bin/bash
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_2d}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
cd "$ROOT"
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
echo "--- 短跑（nx=86 ny=30, end_time=4e-6）---"
timeout 3600 "$MOOSE" -i gibbs2d.i Mesh/gen/nx=86 Mesh/gen/ny=30 \
    Executioner/end_time=4.0e-6 Outputs/exo/enable=false \
    Outputs/checkpoint/enable=false > run.log 2>&1
echo "rc=$?"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'JIT compile failed' > jit.txt
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'Solve Did NOT Converge' > ncv.txt
echo "JIT 失败 = $(cat jit.txt)   未收敛 = $(cat ncv.txt)"
echo "--- 错误 ---"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A6 -m2 '\*\*\* ERROR' | head -20
echo "--- 时间步 ---"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -E '^Time Step|Solve Converged' | tail -8
echo "--- CSV 表头 ---"
head -1 gibbs2d_out.csv 2>/dev/null
echo "--- CSV 末行 ---"
tail -1 gibbs2d_out.csv 2>/dev/null
cp -f run.log gibbs2d_out.csv jit.txt ncv.txt "$SAVE/" 2>/dev/null