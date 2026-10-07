#!/bin/bash
# _r74_outer2.sh —— **只投影外侧（已确认生效）** 的 600 步复验
#
# ## 与 `m3fp10` 的关系
# `m3fp10` 的 `excl` 恒为 `None`（§77）⇒ 那次等价于"全投影"。
# 本次 `vmap` 已挂上（§74 的修），**正对照** `_r74_ctrl.sh` 已证：
#   同一配置下 step 20/40 的 `Vt` **不同** ⇒ 新分支**确实生效** ✅
#
# ## 判据（**先写死；且必须读 600 步的终态，不许读中途值**——§77 教训 1）
#   P-1 `nslab_n` 在 **step 600** 仍 = **3**（对照 `m3fp0` 给 3；旧全投影给 2）—— **主判据**
#   P-2 `f_flat`(600) ≥ **0.08**（旧全投影给 0.161；不投影给 0.018）
#   P-3 判词（600）仍为 **a 快（拉长）**
#   P-4 `box_touch_core == 0`
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
TAG=m3out10b
rm -rf "_exp/_bk_mb/dry_$TAG"
echo "=== 只投影外侧 v2（600 步）  $(date '+%F %T')"
$PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --facet-proj 10 \
  --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_r74_${TAG}.log" 2>&1
echo "=== rc=$?  $(date '+%F %T')"
