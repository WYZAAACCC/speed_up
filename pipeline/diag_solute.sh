#!/bin/bash
# 诊断含溶质版的 dt 被砍问题
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1c_test || exit 1

echo "=== 发散发生的规律（前 20 次）==="
grep -n 'DIVERGED_ITS\|DIVERGED_MAX_IT\|Time Step' run.log | head -40

echo
echo "=== 非线性残差的演化 ==="
grep 'Nonlinear |R|' run.log | head -30

echo
echo "=== MOOSE 有没有能按变量表达式给初值的 IC ==="
ls /root/moose/framework/src/ics/ | head -30
