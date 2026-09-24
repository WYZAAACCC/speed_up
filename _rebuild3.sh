#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh; conda activate moose
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_fix_table.py || exit 3
cd /root/bench/ExaCA-master/build
make -j20 > make5.log 2>&1 || { grep -m 10 'error' make5.log; exit 5; }
echo "--- 重建成功"
cd /root/bench/run
echo "=== 跑 Ti64 单算例（30s 上限）:"
timeout 60 /root/bench/ExaCA-master/build/bin/ExaCA Inp_Ti0.json 2>&1 | grep -v Kokkos | tail -18
ls -la Ti_seed0.vtk 2>/dev/null