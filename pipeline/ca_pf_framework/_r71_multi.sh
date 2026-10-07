#!/bin/bash
# _r71_multi.sh —— **最终验收（第一轮）**：多板条构型 + 保面机制
#
# ## 为什么是这一步
# §65–§69 已在**单板条**上确认：保面机制使
#   `f_flat` 0.005 → **0.106**（×21）、`v_a/v_w` 1.70 → **13.6–19.8**（理论 **8.93**）。
# 但**用户条件 1/2 讲的是多根板条堆叠成块** ⇒ 必须在多板条构型上复测。
#
# ## 配置（与 `dry_mb1s62` 逐项相同，只差 `--facet-proj`）
#   N=96 / Δx=62.5 nm / 盒 6 µm / `--laths 1,1,1`（3 根同类板条堆叠）
#   ⇒ `t/Δx = 10.16`（§33 的分辨率判据）
#
# ## 判据（**先写死**）
#   M-1 **`f_flat` ≥0.08**（对照：不开时 ~0.016，见 §60）
#   M-2 **`nslab_n == 3`**（3 根仍分得开）且 `box_touch_core == 0`
#   M-3 `v_a/v_w ≥ 3`（对照：不开时 1.59–1.70）
#   M-4 体积增长量级不破（`Vt` 与不开时同量级）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 多板条 + 保面  $(date '+%F %T')"
for SPEC in "m3fp10:10" "m3fp0:0"; do
  TAG="${SPEC%%:*}"; NP="${SPEC#*:}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  facet_proj=$NP  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
    --laths 1,1,1 --multi-block --block-gap-nm 0 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj "$NP" \
    --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r71_${TAG}.log" 2>&1 &
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
done
wait
echo "=== 完成 $(date '+%F %T')"
