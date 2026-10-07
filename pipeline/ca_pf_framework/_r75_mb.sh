#!/bin/bash
# _r75_mb.sh —— **用户条件 3**：多**块**构型 + 已验收的保面机制
#
# ## 为什么是这一条
# §80 已把"多根板条堆叠成**一个**块 + 保面"验收通过（`nslab_n=3` 全程、
# `f_flat` 0.115 vs 对照 0.018、判词翻成"拉长"）。
# 用户条件 3 讲的是**多个块之间相互影响并自协调** ⇒ 必须在**两块**构型上复测。
#
# ## 配置（与 `_r30_mb1L.sh` 同族，但按 §33 的分辨率判据把 Δx 减半）
#   N=96 / **Δx=62.5 nm** / 盒 6 µm / `--laths 1,1,1,3,3,3`（**2 块 × 3 根**）
#   `--block-gap-nm 2500`（P1-30 已修 ⇒ 间距**精确兑现**；两块端面间隙 ~900 nm）
#   `--facet-proj 10` / 600 步
# ⚠ 记账：这是"Δx + 盒 + 模式（单块→两块）"的混合对照，**不是纯刻面效应**。
#
# ## 判据（**先写死**）
#   B-1 **`nf2(t=0) == 0`**（两块初始分离；P1-30 的守卫）
#   B-2 **`nf2` 单调增**（两块真的相遇并产生异变体界面）—— 条件 3 的操作化
#   B-3 **`f_flat` 终态 ≥0.08**（保面在**多块**下也成立）
#   B-4 `box_touch_core == 0` 全程
#   B-5 `E_el_J` 与 `r_selfac` 的变化（自协调：`BLOCK_SELFAC` 的 P-SA-1 量）—— 只记录
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
for SPEC in "mb2fp10:10" "mb2fp0:0"; do
  TAG="${SPEC%%:*}"; NP="${SPEC#*:}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  facet_proj=$NP  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
    --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 2500 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj "$NP" \
    --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r75_${TAG}.log" 2>&1 &
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
done
wait
echo "=== 完成 $(date '+%F %T')"
echo '### J-0 守卫（两块的初始接触）'
grep -E '精确判据|块心间距|质心距' _w2_r75_mb2fp10.log | head -4
