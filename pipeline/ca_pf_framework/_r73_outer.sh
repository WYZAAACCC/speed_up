#!/bin/bash
# _r73_outer.sh —— 用户裁定后的复验：**只投影外侧**（保根数优先）
#   与 `m3fp10` 只差 `facet_project()` 里的排除掩码（现在是"外表面定盒子"）。
#   判据：`nslab_n` 应从 2 回到 **3**（对照 `m3fp0` 是 3），且 `f_flat` 仍 ≥0.08。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 只投影外侧（保根数）  $(date '+%F %T')"
TAG=m3out10
rm -rf "_exp/_bk_mb/dry_$TAG"
$PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --facet-proj 10 \
  --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_r73_${TAG}.log" 2>&1
echo "=== rc=$?  $(date '+%F %T')"
