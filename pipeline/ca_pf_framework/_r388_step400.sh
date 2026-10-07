#!/usr/bin/env bash
# _r388_step400.sh —— 消掉 `§176.4` 的**步数混杂**：step 400 的同步数对比 + 可重复性核对
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python

echo "################ ① §173：saSet2(基准集) vs permB1(置换集)，**都在 step 400**"
for A in saSet2 permB1_400; do
  echo "---- $A ----"
  $PY -u _r357_selfac_geom.py "$A" step=400 2>&1 \
    | grep -E '自证|F2 面 =|rank-1|百分位' || true
done

echo
echo "################ ② 可重复性核对：permB1_400 的前 200 步 vs permB1_200"
$PY -u _r350_f2inert.py permB1_400 permB1_200 2>&1 | tail -12 || true
