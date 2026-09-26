#!/bin/bash
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_fixb}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
mkdir -p "$ROOT" "$SAVE"; cd "$ROOT"
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
i=0
for K in 1.0e+06 1.0e+04 1.0e+03 1.0e+02 1.0e+01; do
  i=$((i+1))
  tag="k$i"
  sed "s/1\.000000e+06/$K/g" /mnt/f/speed_up/pipeline/gibbs/stage1_meltpool_gibbs.i > "$tag.i"
  # 自检：确认替换真的生效（教训 7：先确认参数生效）
  nk=$(grep -c "constant_expressions = '$K'" "$tag.i")
  echo "=== k_att = $K   (tag=$tag, 命中常数行 $nk 处) ==="
  timeout 700 "$MOOSE" -i "$tag.i" Mesh/gen/nx=86 Mesh/gen/ny=30 \
      Executioner/end_time=1.0e-6 Outputs/exo/enable=false \
      Outputs/checkpoint/enable=false > "L$tag.log" 2>&1
  rc=$?
  div=$(grep -c DIVERGED "L$tag.log")
  conv=$(grep -c 'Solve Converged' "L$tag.log")
  last=$(grep -E '^Time Step' "L$tag.log" | tail -1)
  echo "rc=$rc  DIVERGED=$div  Converged=$conv   最后: $last"
  cp -f "$tag.i" "L$tag.log" "$SAVE/" 2>/dev/null
done