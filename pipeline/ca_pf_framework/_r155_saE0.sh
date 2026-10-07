#!/bin/bash
# _r155_saE0.sh —— **`§112` 的机制归因**：`r` 上升是不是弹性驱动造成的？
#
# ## 为什么（`§112` 第四节留下的问题）
#
# 自协调实验（同几何 `sgG`）终态：
#   * `saOddG`（可自协调集）：`r` 0.0487 → **0.0775**（**上升**）
#   * `saSet2`（不可自协调集）：`r` 0.5423 → **0.6167**（**上升**）
#   ⇒ **两臂都远离各自的下界** ⇒ **动力学不会把组织推向自协调**（SA-1 FAIL）。
#
# 而 `nf2` 从 0 涨到 1352 / 1922 ⇒ 块早已互相挤压。
# 【推理】上升来自**碰撞改变体积分数**。但**碰撞是弹性的**（`Δed` 项）
# 还是纯几何的（谁先被挡住谁少长）？—— **这个没有测。**
#
# ## 判据（**先写死**）
#   与 `saSet2` / `saOddG` **逐项相同**，只加 `--el-scale 0`（关掉弹性驱动力）。
#   **E-1** 若 el=0 时 `r` **不再上升**（趋势 ≤ 0）⇒ **上升是弹性碰撞造成的**；
#   **E-2** 若 el=0 时 `r` **仍然上升** ⇒ 上升是**几何**的（与弹性无关）；
#   **E-3** 两臂 `box_touch_core == 0` 全程、`nf2(t=0) == 0`（隔离有效）。
#
# ⚠ 记账：`--el-scale 0` 是**大扰动**（总驱动力里少了一项）⇒
#   只能比**趋势的符号**，**不得**跨 el 档比绝对值（`§95` 的老规矩）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"
SET2="1,1,2,2,3,3,4,4,7,7,8,8"

run() {   # run <tag> <laths>
  local TAG="$1" LATHS="$2"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  laths=$LATHS  --el-scale 0  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
    --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm 1300 --el-scale 0 \
    --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 4 --tag "$TAG" --out _exp/_bk_mb > "_w2_r155_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R155 自协调的弹性归因开始 $(date '+%F %T')"
run saOddGE0 "$ODD"  &
run saSet2E0 "$SET2" &
wait
echo "=== R155 结束 $(date '+%F %T')"
