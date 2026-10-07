#!/usr/bin/env bash
# _r381_fourd.sh -- 四个合格指派在 step 200 上的 §173 分布（n=2 → n=4）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for A in saSet2DT200 permB1_200 permB4_200 permB5_200; do
  echo "######## $A"
  $PY -u _r357_selfac_geom.py "$A" step=200 2>&1 \
    | grep -E '自证|F2 面 =|rank-1|百分位' || true
done
echo
echo "######## beta_h_min 的定义位置"
grep -rn 'def beta_h_min' --include=*.py . | head -5
echo
echo "######## 6.477 的来源"
grep -rn '6\.477\|650' --include=*.py . | grep -iv 'test' | head -12
