#!/bin/bash
# _r57_adv.sh —— **E-1（第一步）**：扫平流格式，看 `M(θ)` 的非凸性有没有被兑现。
#
# ## 背景（`R30_AUDIT_LEDGER.md` §44）
# 判据 `F(θ) = v + v″ < 0` ⇒ 该取向被跳过 ⇒ **自发刻面**。
# **实测：现有的 `M(θ)` 本身就非凸**（`F<0` 覆盖 **0°–21.4°**，即尖端附近）
# ⇒ 按判据，尖端**本来就该刻面**；而引擎给 `v_a/v_w` = 1.4–1.7（≈ 没刻面）。
# ⇒ 嫌疑在**平流格式对非凸 `v(n)` 的处理**（普通迎风会给出非熵解 ⇒ 磨圆刻面）。
#
# ## 本实验（**不改任何代码**，只改 `--adv`）
#   三条臂，配置与 `_r54_single.sh` 逐项相同（单根孤立板条、N=64、Δx=62.5、400 步），
#   **只差 `--adv`**：`proj2`（默认）/ `upwind`（Godunov 型）/ `central`。
#
# ## 判据（**先写死**）
#   A-1 若有任一格式把 `v_a/v_w` 从 **1.4–1.7** 抬到 **≥7**
#       ⇒ **非凸性被兑现**，根因是格式 ⇒ 不需要新物理通道；
#   A-2 若三种格式全在 1.5 附近 ⇒ `M(θ)` 的非凸性**完全没被兑现**
#       ⇒ 需要在引擎里**显式实现熵格式/凸包**（P1-31 升级为确认缺陷）；
#   A-3 ⚠ 同时看 `d(n)`（厚度钉扎，现 ≈0.05）与 `box_touch_core`，确认没把别的东西改坏。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== E-1 平流格式对照  $(date '+%F %T')"
for ADV in proj2 upwind central; do
  TAG="adv_${ADV}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- adv=$ADV  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --adv "$ADV" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r57_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== E-1 完成 $(date '+%F %T')"
