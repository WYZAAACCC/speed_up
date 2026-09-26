#!/bin/bash
# 正对照 + 定位：原始 C 版 vs Gibbs 版，同网格同 CLI
#   对照组 = stage1_meltpool_gibbs.i.orig（= 生产 stage1_meltpool_c.i 逐位副本）
#   若对照组也挂 ⇒ 问题在网格/CLI，不在我的改动
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_diag}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
mkdir -p "$ROOT" "$SAVE"; cd "$ROOT"
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
cp -f "$HERE/../stage1_meltpool_gibbs.i.orig" ctrl.i 2>/dev/null
[ -f ctrl.i ] || cp -f /mnt/f/speed_up/pipeline/gibbs/stage1_meltpool_gibbs.i.orig ctrl.i

run_one () {
  tag=$1; inp=$2
  echo "=============================================================="
  echo " $tag   ($inp)"
  echo "=============================================================="
  timeout 1500 "$MOOSE" -i "$inp" Mesh/gen/nx=86 Mesh/gen/ny=30 \
      Executioner/end_time=2.0e-6 Outputs/exo/enable=false \
      Outputs/checkpoint/enable=false > "log_$tag.log" 2>&1
  echo "rc=$?"
  n1=$(grep -c DIVERGED "log_$tag.log")
  n2=$(grep -c 'Solve Converged' "log_$tag.log")
  n3=$(grep -c 'JIT compile failed' "log_$tag.log")
  echo "DIVERGED=$n1  SolveConverged=$n2  JIT失败=$n3"
  echo "--- 时间步推进 ---"
  grep -E '^Time Step' "log_$tag.log" | tail -3
  echo "--- 错误 ---"
  sed "s/\x1b\[[0-9;]*m//g" "log_$tag.log" | grep -A4 -m1 '\*\*\* ERROR' | head -8
  echo "--- CSV 表头 ---"
  head -1 "${inp%.i}_out.csv" 2>/dev/null
  echo "--- CSV 末两行 ---"
  tail -2 "${inp%.i}_out.csv" 2>/dev/null
  cp -f "log_$tag.log" "$SAVE/" 2>/dev/null
}

run_one ctrl  ctrl.i
run_one gibbs gibbs2d.i
echo
echo "全部复制到 $SAVE"