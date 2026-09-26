#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/pc; rm -rf $R; mkdir -p $R; cd $R
for K in 0 1.0e4; do
  sed "s/@EPSK@/$K/g" /mnt/f/speed_up/pipeline/gibbs/validated/probeC_mesh_displacement.i > "pc_$K.i"
  echo "=== EPSK = $K ==="
  timeout 900 /root/projects/gibbs/gibbs-opt -i "pc_$K.i" > "L_$K.log" 2>&1
  echo "rc=$?  JIT失败=$(grep -c 'JIT compile failed' L_$K.log)"
  sed "s/\x1b\[[0-9;]*m//g" "L_$K.log" | grep -A6 -m1 '\*\*\* ERROR' | head -12
  head -1 "pc_${K}_out.csv" 2>/dev/null
  echo "--- 首行 ---"; sed -n 2p "pc_${K}_out.csv" 2>/dev/null
  echo "--- 末行 ---"; tail -1 "pc_${K}_out.csv" 2>/dev/null
done
mkdir -p /mnt/f/speed_up/pipeline/gibbs/results_probeC
cp -f L_*.log pc_*.i pc_*_out.csv /mnt/f/speed_up/pipeline/gibbs/results_probeC/ 2>/dev/null