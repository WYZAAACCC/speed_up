#!/bin/bash
# _r77_iso.sh —— **用户条件 ③ 的决定性隔离**：块与块之间到底有没有"相互影响"？
#
# ## 为什么现有证据不够
# R75 的 B-2 判据是 `nf2` 单调增（0→53），它证明的是两块**相遇**
# （异变体界面格面数增加），**不证明相互影响**：两块各自长大、几何上撞上，
# 一样会给 `nf2 > 0`，而**弹性耦合完全可以为零**。
# 用户条件 ③ 的原话是「块与块之间可以**相互影响**产生**自协调**的组织」⇒
# 必须做**只差块 1 在不在**的隔离。
#
# ## 隔离设计（严格单变量，`AGENTS.md §3.3-21`）
# 两块臂里块 0 的种子 = 3 根 V1，块心 `c0 − 1250·u`，u=[0,1,0]，n*=NPF[1]。
# 而**单块臂**（`--laths 1,1,1`、不开 `--multi-block`）走 `_bk_exp.py:752` 的
# `else` 支：同样是 3 根 V1、同样的 n*/w/a（都用 `laths[0]=1`）、
# 种在 `c0 + off·n*`。
#
# ⇒ 两者**只差一个平移**（块心从 y=1.75 µm 变成 y=3.00 µm）。
#   而盒是**周期**的、块不碰壁（`box_touch_core=0`）⇒ 单块构型下
#   平移是**严格对称**（最近周期像距恒为 6 µm），且两个位置都是 Δx 的整数倍
#   （1.75 µm = 28Δx、3.00 µm = 48Δx）⇒ **网格相位也一致**。
#   **已核实**：种子的 `along` 方向在两臂里都取 `a_ax(V1)`（符号不影响，
#   板条关于自身中心对称）。
# ⇒ 这是"**只差块 1 在不在**"的干净对照，**不需要新开关**。
#
# ## 机制归因（第二层）
# `--el-scale 0` 关掉弹性驱动力 ⇒
#   Δ(el=1) = 两块 − 单块  ≠ 0  而  Δ(el=0) ≈ 0   ⇒ 耦合**是弹性的**
#   Δ(el=1) ≠ 0 且 Δ(el=0) ≠ 0                    ⇒ 耦合**不是**（只）弹性的
#
# ## 预先写死的判据（**先写死再看数**）
#   I-1 隔离有效性：单块臂 `nblk_sig == 1`、两块臂 `nblk_sig == 2`（量具自证）
#   I-2 无影响：块 0 的 `blk_span_nm[0]` / `blk_alen_nm[0]` / `blk_wlen_nm[0]`
#       在两臂里**逐步一致到 < 1%（或 < 1Δx）** ⇒ 块 1 对块 0 **无影响**
#   I-3 有影响：任一时间点的差异 > 2% ⇒ **有影响**（并记录首次偏离的步数）
#   I-4 归因：见上（el=0 的两臂同法比）
# ⚠ 记账：单块臂的 `--laths 1,1,1` 使 `nv=3`、变体数=1 ⇒ `f_var`/`r_selfac`
#   与两块臂**不可比**（那两列本就不该跨构型比）。本脚本只比**块 0 的几何**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--arm dry --N 96 --dx-nm 62.5 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --facet-proj 10 --out _exp/_bk_mb"

run() {   # run <tag> <laths> <extra...>
  local TAG="$1"; shift
  local LATHS="$1"; shift
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  laths=$LATHS  extra='$*'  $(date '+%T')"
  $PY -u _bk_exp.py $COMMON --laths "$LATHS" "$@" \
      --tag "$TAG" > "_w2_r77_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

# ① 单块 V1（块 0 的隔离参照）
run mo1fp10  "1,1,1"                 &
# ② 两块 V1|V3，弹性关（机制归因）
run mo2el0   "1,1,1,3,3,3" --multi-block --block-gap-nm 2500 --el-scale 0 &
# ③ 单块 V1，弹性关（机制归因的参照）
run mo1el0   "1,1,1"        --el-scale 0 &
wait
echo "=== R77 全部完成 $(date '+%F %T')"
