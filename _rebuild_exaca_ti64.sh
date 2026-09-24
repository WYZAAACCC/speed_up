#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
set -x
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_ti64_table.py
cd /root/bench/ExaCA-master/build
make -j20 > make3.log 2>&1 || { tail -40 make3.log; exit 5; }
echo "--- 重建成功"
ls -la bin/ExaCA