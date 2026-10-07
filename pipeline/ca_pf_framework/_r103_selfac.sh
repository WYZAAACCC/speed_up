#!/bin/bash
# _r103_selfac.sh —— **用户条件 ③ 的"自协调"合格实验**（首个满足判据要求的盒子）。
#
# ## 为什么这样设计（判据链见 R30_AUDIT_LEDGER §88/§94/§101）
#
# 1. `_r88` 用**纯组合**方法（只吃 `EPS0`）证明：64 个自协调六元组**唯一地**对应
#    配对 **(1,2)(3,4)(5,6)(7,8)(9,10)(11,12)**，"每对取一个"。
# 2. `_r78` 的单纯形最小化：`{1..6}` 的 `r_min = **0.4828**`，
#    而"每对一个"的集合 `r_min ≈ **0**`。
#    ⇒ **只有"每对一个"的变体集，`r_selfac` 才有降到 0 的空间。**
#    （`§16` 的 `eng_mb2/3` 用 `{1..6}` ⇒ 从来没在那一族里 ⇒ 那就是"远未达最优"的原因。）
# 3. `_r98/_r100/_r102` 的几何扫描：`--plate-L 1600` 时 6 个块**t=0 就重叠**
#    （`nf2(t=0)` = 1845–2897）。扫出**可用构型**：
#      N=112（7 µm 盒）/ L=1000 / W=500 / T=510 / **gap=1300** ⇒ `nf2(t=0) = 0` ✅
#      且 `nblk_sig=6`、`blk_laths=2/2/2/2/2/2`（**条件② 同时满足**）
#      分辨率 `T/Δx = 510/62.5 = 8.16` ≥ 8（§33 判据）✅
#
# ## ★ 预登记判据（**先写死再看数**）
#
# | # | 判据 | 若成立说明 |
# |---|---|---|
# | **SA-0** | 两臂 `nf2(t=0) == 0` 且 `nblk_sig == 6`（量具自证） | 隔离有效 |
# | **SA-1** | `saPair`（不可自协调集）的 `r_selfac` **下降** | **动力学主动走向自协调** ← 本实验的核心 |
# | **SA-2** | `saOdd`（可自协调集）的 `r_selfac` **保持在低位**（末态 ≤ 0.20） | 自协调组合**稳定** |
# | **SA-3** | `saPairE0`（`el=0`）的 `r_selfac` **不下降**（或降幅显著小于 `saPair`） | 驱动力**是弹性的** |
# | **SA-4** | 三臂 `box_touch_core == 0` 全程 | 不撞壁 |
#
# ⚠ **记账（必须随结论一起报）**
#   * 变体是**预先规定**的（`--laths`）⇒ 本实验测的是**体积分数漂移**，
#     **不是变体选择**（选择要 `--arm eng --nuc-init`，见历史 P-SA-1）。
#   * `saOdd` 的 `r` **初始就低**（≈0）⇒ 它测的是"**保持**"，不是"**达到**"。
#   * 两臂的 `G` 不同 ⇒ **裸 `r_selfac` 不可跨臂直接比**，
#     必须同时报 `r_norm = (r − r_min(G))/(1 − r_min(G))`（`§89` 的规程）。
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
    --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm 1300 \
    --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb "$@" > "_w2_r103_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R103 自协调实验开始 $(date '+%F %T')"
run saPair   "$PAIR"                 &
run saOdd    "$ODD"                  &
run saPairE0 "$PAIR" --el-scale 0    &
wait
echo "=== R103 结束 $(date '+%F %T')"
