#!/bin/bash
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_diag}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
cd "$ROOT"
cp -f /mnt/f/speed_up/pipeline/gibbs/stage1_meltpool_nogam.i .
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
echo "=== 隔离测试：新 f_loc/M，**无 Gam** ==="
timeout 1500 "$MOOSE" -i stage1_meltpool_nogam.i Mesh/gen/nx=86 Mesh/gen/ny=30 \
    Executioner/end_time=2.0e-6 Outputs/exo/enable=false \
    Outputs/checkpoint/enable=false > log_nogam.log 2>&1
echo "rc=$?"
echo "DIVERGED=$(grep -c DIVERGED log_nogam.log)  Converged=$(grep -c 'Solve Converged' log_nogam.log)"
grep -E '^Time Step' log_nogam.log | tail -3
echo "--- 错误 ---"
sed "s/\x1b\[[0-9;]*m//g" log_nogam.log | grep -A4 -m1 '\*\*\* ERROR' | head -8
echo "--- CSV 末行 ---"
tail -1 stage1_meltpool_nogam_out.csv 2>/dev/null
cp -f log_nogam.log "$SAVE/" 2>/dev/null