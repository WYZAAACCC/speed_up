#!/bin/bash
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_diag}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
cd "$ROOT"; cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
for K in 1.0e+06 1.0e+04 1.0e+02; do
  tag=$(echo "$K" | tr -d ' .+')
  sed "s/1\.000000e+06/$K/g" /mnt/f/speed_up/pipeline/gibbs/stage1_meltpool_gibbs.i > "ga_$tag.i"
  echo "=== k_att = $K ==="
  timeout 900 "$MOOSE" -i "ga_$tag.i" Mesh/gen/nx=86 Mesh/gen/ny=30 \
      Executioner/end_time=2.0e-6 Outputs/exo/enable=false \
      Outputs/checkpoint/enable=false > "lg_$tag.log" 2>&1
  echo "rc=$?  DIVERGED=$(grep -c DIVERGED lg_$tag.log)  Converged=$(grep -c 'Solve Converged' lg_$tag.log)"
  grep -E '^Time Step' "lg_$tag.log" | tail -2
  echo "  CSV末行: $(tail -1 ga_${tag}_out.csv 2>/dev/null | cut -c1-120)"
  cp -f "lg_$tag.log" "$SAVE/" 2>/dev/null
done