#!/bin/bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _fix_dup.py || exit 2
echo "=== E1 复测（envelope 应回到 PASS）:"
OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python pipeline/ca_pf_framework/verify_ca3d_envelope.py 2>&1 | sed -n '1,9p'
echo "=== 三模式几何:"
OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python _verify_cell_geom.py