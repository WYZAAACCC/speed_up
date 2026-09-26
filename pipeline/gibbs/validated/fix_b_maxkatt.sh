#!/bin/bash
set +u
cd /root/work/g2d
MOOSE=/root/projects/gb_jac/gb_jac-opt
SRC=/mnt/f/speed_up/pipeline/gibbs/stage1_meltpool_gibbs.i
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
for K in 1.0e+04 1.0e+03; do
  t=$(echo "$K" | tr -d '.+')
  sed "s/1\.000000e+06/$K/g" "$SRC" > "kb_$t.i"
  echo "=== k_att = $K ==="
  timeout 300 "$MOOSE" -i "kb_$t.i" Mesh/gen/nx=86 Mesh/gen/ny=30 \
      Executioner/end_time=1.0e-6 Outputs/exo/enable=false \
      Outputs/checkpoint/enable=false > "Lb_$t.log" 2>&1
  echo "rc=$?"
  echo "DIVERGED=$(grep -c DIVERGED Lb_$t.log)"
  echo "Converged=$(grep -c 'Solve Converged' Lb_$t.log)"
  grep -E '^Time Step' "Lb_$t.log" | tail -1
  cp -f "Lb_$t.log" "kb_$t.i" /mnt/f/speed_up/pipeline/gibbs/results_fixb/ 2>/dev/null
done