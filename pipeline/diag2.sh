#!/bin/bash
# 仔细诊断：到底什么在限制步长
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1c_test || exit 1

echo "=== 计数 ==="
echo "DIVERGED_ITS   : $(grep -c DIVERGED_ITS run.log)"
echo "DIVERGED_MAX_IT: $(grep -c DIVERGED_MAX_IT run.log)"
echo "Solve Converged: $(grep -c 'Solve Converged' run.log)"
echo "Time Step 行数 : $(grep -c 'Time Step' run.log)"

echo
echo "=== dt 的锯齿（前 60 个 Time Step 行）==="
grep 'Time Step' run.log | head -60

echo
echo "=== 第一个发散点的上下文 ==="
n=$(grep -n 'DIVERGED' run.log | head -1 | cut -d: -f1)
if [ -n "$n" ]; then
    sed -n "$((n-25)),$((n+3))p" run.log
else
    echo "（没有 DIVERGED —— 说明没有发散，只是步长涨得慢）"
fi
