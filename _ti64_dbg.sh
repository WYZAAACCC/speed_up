#!/bin/bash
for p in $(ps -eo pid,args | grep -E '[_]ti64_compare|[E]xaCA /root' | awk '{print $1}'); do kill $p 2>/dev/null; done
sleep 1
source /root/miniconda3/etc/profile.d/conda.sh; conda activate moose
cd /root/bench/run
echo "=== 表文件头:"; head -3 irf_ti64_table.csv; wc -l irf_ti64_table.csv
echo "=== Ti64.json:"; cat Ti64.json
echo "=== 单跑 Ti64 算例（前 25 s 输出）:"
timeout 25 /root/bench/ExaCA-master/build/bin/ExaCA Inp_Ti0.json 2>&1 | grep -v Kokkos | head -30
echo "(timeout 25s 结束)"
ls -la Ti_seed0*.vtk 2>/dev/null | head -3