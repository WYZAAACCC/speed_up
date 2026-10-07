#!/bin/bash
# _r120_scan3.sh —— 六块盒子的**第三轮**几何扫描：**双判据**（新增规程⑧）。
#
# ## 判据（**两条都要过**）
#   **块间**：`nf2(t=0) == 0`（异变体不接触）
#   **块内**：`cov(t=0) ≥ 0.85` 且每对 β 占比 ≤ 0.25（同变体界面接得上）
#
# ## 为什么加第二条（`§99` 第六节）
# 前两轮我只用了第一条 ⇒ 放行了 `cov(t=0) = 0.53` 的 R110 几何
# （`L=600/W=350/T=510`；β 占比 0.26–0.33，远高于底噪 0.15）⇒ **t=0 就把块内 F3 播坏了**。
#
# 已实测的**合格板条参数**来自 R75/R77（`cov(t=0)` = **1.079 / 0.958**）：
#   **L=1600 / W=700 / T=635**（T/Δx = **10.16 胞**）
# 而不合格的是 **T=510**（8.16 胞）⇒ **种子厚度的格点相位是关键**（`_bk_exp.py:708-721` 同族）。
# ⇒ 本轮**固定 T=635、W=600–700**，只调 **N / L / gap**。
#
# 内存（nreg=13）：N=96 ⇒ ≈2.6 GB；N=112 ⇒ ≈4.2 GB；N=128 ⇒ ≈6.2 GB ⇒ **分批**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"

run() {   # run <tag> <N> <L> <W> <T> <gap>
  local TAG="$1" NN="$2" LL="$3" WW="$4" TT="$5" GAP="$6"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T "$TT" --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$ODD" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb > "_w2_r120_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R120 双判据扫描开始 $(date '+%F %T')"
# 批 1（N≤112，≈2.6–4.2 GB/臂）
run t1N96L800  96  800  600 635  900 &
run t1N96L1000 96  1000 700 635  700 &
run t1N112L1000 112 1000 700 635 1100 &
run t1N112L800  112 800  600 635 1200 &
wait
echo "=== 批 1 结束 $(date '+%F %T')"
# 批 2（N=128，≈6.2 GB/臂 —— 只并发 2）
run t2N128L1600 128 1600 700 635 1100 &
run t2N128L1200 128 1200 700 635 1200 &
wait
echo "=== 批 2 结束 $(date '+%F %T')"
# 批 3
run t3N128L1000 128 1000 600 635 1300 &
run t3N112L1200 112 1200 700 635 900 &
wait
echo "=== R120 全部结束 $(date '+%F %T')"
