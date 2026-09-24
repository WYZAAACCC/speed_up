#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_fix_inc.py
cd /root/bench/ExaCA-master/build
make -j20 > make4.log 2>&1 || { grep -m 12 'error' make4.log; exit 5; }
echo "--- 重建成功:"; ls -la bin/ExaCA