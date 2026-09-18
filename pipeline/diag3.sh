#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1c_test || exit 1

echo "=== 输入文件里的 optimal_iterations（确认改动生效）==="
grep -A6 'TimeStepper' in.i

echo
echo "=== MOOSE 报告的砍步长原因 ==="
grep -i 'cutting\|cut back\|reducing\|timestep\|Time step decreased\|Solve Did NOT' run.log | head -20

echo
echo "=== Time Step 4 前后的完整输出 ==="
n=$(grep -n 'Time Step 4,' run.log | sed -n '2p' | cut -d: -f1)
[ -n "$n" ] && sed -n "$((n-30)),$((n+2))p" run.log

echo
echo "=== 非线性迭代数分布 ==="
awk '/Nonlinear \|R\|/{c++} /Solve Converged|Solve Did NOT/{print c; c=0}' run.log | sort | uniq -c
