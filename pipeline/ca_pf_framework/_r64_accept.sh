#!/bin/bash
# _r64_accept.sh —— **椭圆面内极曲线**的验收臂（§52 的设计）
#
# ## 判据（**先写死**）
#   V-1 **主判据**：`--mob-iform ellipse --mob-ratio 9` 的 `v_a/v_w`（v2 口径）**≥ 6**
#       对照：现形式（`exp2`）实测 **1.70**；理论上限（Wulff 形）**8.93**
#   V-2 `d(n)/d(a)` 保持很小（厚度钉扎；`exp2` 实测 ≈0.033）
#   V-3 `box_touch_core == 0`
#   V-4 ⚠ 若 V-1 不过：先确认新分支**确实被走到**（看 `_mfac_dt` 是否变化），
#       再判"光滑演化给出角平均"是否就是极限（§45 的结论）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 椭圆形式验收  $(date '+%F %T')"
for SPEC in "ell9:--mob-iform ellipse --mob-ratio 9" \
            "ell3:--mob-iform ellipse --mob-ratio 3" \
            "ell20:--mob-iform ellipse --mob-ratio 20"; do
  TAG="${SPEC%%:*}"; FLAGS="${SPEC#*:}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  '$FLAGS'  $(date '+%T')"
  # shellcheck disable=SC2086
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    $FLAGS \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r64_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== 完成 $(date '+%F %T')"
