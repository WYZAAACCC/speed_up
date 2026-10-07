#!/bin/bash
# _r141_selfac3.sh —— ★★★ **自协调合格实验（同几何版）**：终于凑齐了。
#
# ## 为什么这次是对的（前面三轮各自的缺口）
#   * `_r110`：三臂几何**不同**（PAIR 集放不下 `sgG`）⇒ 混杂；
#   * `_r135`：PAIR 集 `{1..6}` 在 ODD 已通过的**全部 6 个几何**上放不下
#     （2 崩 + 4 重叠）—— 根因是它的布局轴 `u=[0,1,0]`（一条直线，直线度 0.276）；
#   * `_r137`：改用 `_r108` 挑出的 **集2 `{1,2,3,4,7,8}`**（`r_min` **同为 0.4828**，
#     直线度 **0.013**）⇒ **`s2a` 在 `sgG` 几何上 `nf2(t=0) = 0` ✅**
#   ⇒ **ODD 集与集2 现在有**同一个**可用几何 `sgG`**。
#
# ## 两臂（**同几何**，只差变体集）
# | tag | `--laths` | `G` | `r_min(G)` | 期望 |
# |---|---|---|---|---|
# | `saOddG` | `1,1,3,3,5,5,7,7,9,9,11,11` | `{1,3,5,7,9,11}` | **0.0000** | `r` **保持低位** |
# | `saSet2` | `1,1,2,2,3,3,4,4,7,7,8,8` | `{1,2,3,4,7,8}` | **0.4828** | `r` **下降**（若动力学主动走向自协调） |
# 几何：**N=112 / 7 µm 盒 / Δx=62.5 / L=1000 / W=500 / T=510（T/Δx=8.16）/ gap=1300 /
#        `--facet-proj 10` / 400 步**
#
# ## ★ 预登记判据（**先写死再看数**）
#   **SA-0** 两臂 `nf2(t=0)==0`、`nblk_sig==6`、`blk_nprof==2/2/2/2/2/2`（量具自证）
#   **SA-1** `saSet2` 的 `r_selfac` **下降**（本实验核心：动力学是否**主动**走向自协调）
#   **SA-2** `saOddG` 的 `r_selfac` **保持 ≤ 0.20**
#   **SA-4** 两臂 `box_touch_core == 0` 全程
#
# ⚠ **记账（必须随结论一起报）**
#   * 变体是**预先规定**的（`--laths`）⇒ 测的是**体积分数漂移**，**不是变体选择**。
#   * 两臂 `G` 不同 ⇒ **裸 `r_selfac` 不可跨臂直接比** ⇒ 必须同时报
#     `r_norm = (r − r_min(G))/(1 − r_min(G))`。
#   * `cov(t=0)` 有 `L` 依赖（`§100`）⇒ 块内界面质量用 **`cov_norm`**（对该 `L` 的基线）判。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"
SET2="1,1,2,2,3,3,4,4,7,7,8,8"

run() {   # run <tag> <laths>
  local TAG="$1" LATHS="$2"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  laths=$LATHS  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
    --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm 1300 \
    --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb > "_w2_r141_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R141 自协调同几何实验开始 $(date '+%F %T')"
run saOddG "$ODD"  &
run saSet2 "$SET2" &
wait
echo "=== R141 结束 $(date '+%F %T')"
