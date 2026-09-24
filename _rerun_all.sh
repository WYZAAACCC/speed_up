#!/bin/bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _fix_sign.py
cd pipeline/ca_pf_framework
echo "=== A 组（不涉及动力学，应仍 PASS）:"
OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python windowB_pf.py 2>&1 | grep -E 'A0a|A0b' 
echo "=== 判据组:"
OMP_NUM_THREADS=1 timeout 1200 /root/miniconda3/envs/ml/bin/python windowB_bench.py 2>&1 | tail -18