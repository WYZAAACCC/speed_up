#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/bench/run
cp /mnt/f/speed_up/bench/exaca/Inp_SmallDirS_abs.json /mnt/f/speed_up/bench/exaca/Inp_TwoGrain_abs.json .
echo "=== 跑 SmallDirSolidification（20^3, In625）:"
time /root/bench/ExaCA-master/build/bin/ExaCA Inp_SmallDirS_abs.json 2>&1 | grep -v Kokkos | tail -22
echo; echo "=== 输出:"; ls -la /root/bench/run/*.vtk 2>/dev/null | head