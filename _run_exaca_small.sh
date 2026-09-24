#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
mkdir -p /root/bench/run && cd /root/bench/run
cp /mnt/f/speed_up/bench/exaca/*.json /mnt/f/speed_up/bench/exaca/GrainOrientationVectors.csv . 2>/dev/null
ls
echo; echo "=== 跑 Inp_SmallDirSolidification（20^3）:"
time /root/bench/ExaCA-master/build/bin/ExaCA Inp_SmallDirSolidification.json 2>&1 | tail -25
echo; echo "=== 输出文件:"; ls -la | head -20