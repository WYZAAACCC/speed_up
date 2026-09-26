#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/p3d; rm -rf $R; mkdir -p $R; cd $R
cp /mnt/f/speed_up/pipeline/gibbs/validated/proto3d_gibbs_surface.i .
timeout 900 /root/projects/gibbs/gibbs-opt -i proto3d_gibbs_surface.i > run.log 2>&1
echo "rc=$?"
echo "JIT失败=$(grep -c 'JIT compile failed' run.log)  未收敛=$(grep -c 'Solve Did NOT Converge' run.log)"
echo "=== 错误 ==="
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A6 -m2 '\*\*\* ERROR' | head -20
echo "=== CSV ==="
head -1 proto3d_gibbs_surface_out.csv 2>/dev/null
echo "--- 首行 ---"; sed -n 2p proto3d_gibbs_surface_out.csv 2>/dev/null
echo "--- 末行 ---"; tail -1 proto3d_gibbs_surface_out.csv 2>/dev/null
mkdir -p /mnt/f/speed_up/pipeline/gibbs/results_p3d
cp -f run.log proto3d_gibbs_surface.i proto3d_gibbs_surface_out.csv /mnt/f/speed_up/pipeline/gibbs/results_p3d/ 2>/dev/null