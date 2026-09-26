#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/kprobe; rm -rf $R; mkdir -p $R; cd $R
for S in 1 2; do
  sed "s/@SCALE@/$S/g" /mnt/f/speed_up/pipeline/gibbs/validated/probe_scaled_td.i > p.i
  timeout 300 /root/projects/gibbs/gibbs-opt -i p.i > L.log 2>&1
  echo "scale=$S rc=$?  c_max(unused)=$(tail -1 p_out.csv | cut -d, -f2)  c_min=$(tail -1 p_out.csv | cut -d, -f3)"
  grep -A3 -m1 "ERROR" L.log | head -4
  cp -f L.log /mnt/f/speed_up/pipeline/gibbs/results_kernel_scale$S.log 2>/dev/null
done