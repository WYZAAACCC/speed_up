#!/bin/bash
# 显示 cmp_solution.py 输出中"物理量趋势"之后的部分。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
sed 's/\r$//' /mnt/f/speed_up/pipeline/cmp_solution.py > /root/work/cs.py
python3 /root/work/cs.py > /root/work/cs2.txt 2>&1
echo "  --- A 进度 ---"
grep -a '^Time Step' /root/work/slv_cmp/A/run.log | tail -1
grep -a 'Nonlinear |R|' /root/work/slv_cmp/A/run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -3
echo
awk '/物理量的 relL2/,0' /root/work/cs2.txt
