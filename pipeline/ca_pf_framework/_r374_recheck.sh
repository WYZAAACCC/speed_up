#!/usr/bin/env bash
# _r374_recheck.sh -- 用**细化后的 R** 重跑 §173 的两个步 + 另一条臂；并查在跑的 4 条臂
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for A in "saSet2 step=200" "saOddG step=400"; do
  echo "################ _r357 $A"
  $PY -u _r357_selfac_geom.py $A 2>&1 | grep -E '自证|F2 面|R（rank-1|百分位|⇒' | head -8
done
echo
echo "################ 在跑的 4 条臂"
echo "_bk_exp 进程数: $(pgrep -c -f '_bk_exp[.]py' || echo 0)"
for t in permB1_400 saSet2DT200 permB4_200 permB5_200; do
  n=$(ls "_exp/_bk_mb/dry_${t}"/snap_*.npz 2>/dev/null | tail -1)
  printf '  %-14s %s\n' "$t" "${n##*/}"
done
free -g | head -2
