#!/bin/bash
# _r110_selfac2.sh —— **自协调实验 v2**：三臂用**同一几何**（`q600g1200`，已实测分离）。
#
# ## 几何从哪来（每一步都是可证伪的实测，不是推理）
# 1. `_r98`：`--plate-L 1600` 时 6 块**t=0 就重叠**（`nf2(t=0)` = 1845–2897）⇒ 否定。
# 2. `_r100/_r102`：**ODD 集**（`{1,3,5,7,9,11}`）可用 → `sgG` = N=112/L=1000/W=500/gap=1300
#    （`nf2(t=0)=0`、`nblk_sig=6`、`blk_laths=2/2/2/2/2/2`）。
# 3. `_r103`：**PAIR 集**（`{1..6}`）在 `sgG` 几何上**被引擎拒绝**
#    （`ValueError: elongated seed exceeds domain`）—— 因为 PAIR 集的布局轴是
#    `u=[0,1,0]`（**一条直线沿 y**，直线度 0.276），最外侧块顶出盒壁。
# 4. `_r104/_r107/_r109`：缩板条后扫出 **`q600g1200`** =
#    **N=112 / L=600 / W=350 / T=510 / gap=1200 ⇒ `nf2(t=0) == 0` ✅**（PAIR 集）。
#    （同档 `q450g1200` 也过，但板条更小 ⇒ 取大的那个。）
#
# ## 三臂（**同一几何**，只差变体集与 `--el-scale`）
# | tag | `--laths` | `G` | `r_min(G)` | `el` |
# |---|---|---|---|---|
# | `saPair`   | 1,1,2,2,3,3,4,4,5,5,6,6      | {1..6} | **0.4828** | 1 |
# | `saPairE0` | 同上                          | {1..6} | **0.4828** | **0** |
# | `saOdd`    | 1,1,3,3,5,5,7,7,9,9,11,11    | {1,3,5,7,9,11} | **0.0000** | 1 |
#
# ## ★ 预登记判据（**先写死再看数**；与 v1 相同，只是几何更严）
#   **SA-0** 三臂 `nf2(t=0) == 0` 且 `nblk_sig == 6`
#   **SA-1** `saPair` 的 `r_selfac` **下降**（本实验核心：动力学是否**主动**走向自协调）
#   **SA-2** `saOdd` 的 `r_selfac` **保持 ≤ 0.20**
#   **SA-3** `saPairE0`（el=0）**不下降**（或降幅 ≪ `saPair`）⇒ 驱动力是弹性的
#   **SA-4** 三臂 `box_touch_core == 0` 全程
#
# ⚠ **记账**：变体是**预先规定**的 ⇒ 测的是**体积分数漂移**，不是变体选择；
#   两臂 `G` 不同 ⇒ 裸 `r` 不可跨臂比，必须同时报 `r_norm`。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

ODD="1,1,3,3,5,5,7,7,9,9,11,11"
PAIR="1,1,2,2,3,3,4,4,5,5,6,6"

run() {   # run <tag> <laths> [extra...]
  local TAG="$1"; shift
  local LATHS="$1"; shift
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  laths=$LATHS  extra='$*'  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
    --plate-L 600 --plate-W 350 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm 1200 \
    --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb "$@" > "_w2_r110_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R110 自协调实验 v2 开始 $(date '+%F %T')"
run saPair   "$PAIR"              &
run saPairE0 "$PAIR" --el-scale 0 &
run saOdd    "$ODD"               &
wait
echo "=== R110 结束 $(date '+%F %T')"
