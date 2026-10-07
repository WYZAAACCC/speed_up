#!/bin/bash
# _r165_f2test.sh —— **`§122` 补法的受控对照**：F2 配对面能开/关（λ=1 vs λ=0）。
#
# ## 补的是什么（`§122`）
# `windowB_lath.py:23-25` 写着 F1/F2 的 γ **不动**（退回标量 `gamma0`）
# ⇒ **V1/V3 界面与 V1/V5 界面能量一模一样** ⇒ 生长通道**无从选择**。
# 补法（由模型自身的失配导出）：`γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1,‖Δε‖/Δε_ref)]`
#
# ## ★ 关键设计：**两个变体集对这条补法的"敏感度"应当不同**
#
# | 臂 | `G` | 含同 packet 对吗？（配对 = (1,2)(3,4)(5,6)(7,8)(9,10)(11,12)） |
# |---|---|---|
# | `saSet2` | `{1,2,3,4,7,8}` | **含 2 对**：(1,2)、(3,4) ⇒ **有便宜的界面可用** |
# | `saOddG` | `{1,3,5,7,9,11}` | **一对都没有** ⇒ 面内无"便宜对" |
#
# ⇒ **预登记预测**：λ=1 对 `saSet2` 的影响**远大于**对 `saOddG` 的影响。
#    若两者影响相当 ⇒ 说明"配对依赖"不是通过 `‖Δε‖` 在起作用（需重查）。
#
# ## ★ 预登记判据（**先写死再看数**）
#   **G-1** λ=0 的两条臂应与 `§112` 的 `saSet2`/`saOddG` **逐位相同**（开关惰性证明）
#   **G-2** λ=1 时 `saSet2` 的 `r_selfac` **趋势**相对 λ=0 **改变幅度** > `saOddG` 的改变幅度
#           （⇒ 配对依赖确实经"同 packet 便宜"起作用）
#   **G-3** 两臂 `box_touch_core == 0` 全程、`nf2(t=0) == 0`（隔离有效）
#   **G-4** 记录 `E_el/Vt`（`§118/§119` 的强制要求：**不得只报 `r`**）
#
# ⚠ **不预设"哪个对"**：本实验只测"这条补法有没有按预期起作用"，
#   **不判**"促进 packet 好还是促进 6 变体自协调好"（那是物理选择，`§122` 第五节）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"
SET2="1,1,2,2,3,3,4,4,7,7,8,8"

run() {   # run <tag> <laths> <lam>
  local TAG="$1" LATHS="$2" LAM="$3"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  lam=$LAM  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
    --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm 1300 \
    --f2-pair-gamma "$LAM" \
    --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 4 --tag "$TAG" --out _exp/_bk_mb > "_w2_r165_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R165 F2 配对面能对照开始 $(date '+%F %T')"
run saSet2F2 "$SET2" 1.0 &
run saOddGF2 "$ODD"  1.0 &
wait
echo "=== R165 结束 $(date '+%F %T')"
