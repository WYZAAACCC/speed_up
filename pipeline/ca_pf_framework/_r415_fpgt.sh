#!/bin/bash
# _r415_fpgt.sh —— ★★ **`--facet-proj` 的真值实验**（离线重实现已被证伪，改跑真仿真）
#
# ## 为什么必须重跑
# `_r413`（走**真实** `LevelSetMulti.facet_project()`）的 **V-1 正对照 FAIL**：
#   * 引擎里 `facet_excl=1` ⇒ F3 = **1011**、块 = **6**、β 膜 64 胞；
#   * 我的离线重实现（`_r410`）却给 F3 = **0**、块 = **12**、β 膜 1451 胞。
# ⇒ **离线重实现的合成口径不忠实**（根因见 §187：我把投影后的场强行写成二值 `±Δx`，
#   而引擎里的新 `φ` 是**真盒子 SDF**，会向外"claim" 缝里的胞 ⇒ 缝被两场
#   `argmin` 对分、两场**仍然相邻** ⇒ F3 **不会**归零）。
# ⇒ `§186` 的**机理与结论作废**，必须以**真仿真**为准。
#
# ## 本脚本做什么
# 同一构型（N=112、Δx=62.5 nm、12 场、6 块 × 2 板条、块距 1300 nm），
# **只差 `--facet-proj` / `--facet-excl`**，跑 40 步：
#   A `--facet-proj 0 `                 （投影关闭，对照）
#   B `--facet-proj 10 --facet-excl 1`  （**归档行为**，旧的 R73 排除掩码）
#   C `--facet-proj 10 --facet-excl 0`  （本轮改的"修复"）
# 逐 step 读 `nf3` / `blk_nprof` / `nf2`。
#
# ## 判据（预先写死）
#   G-1 三条臂都必须**跑完无 Traceback**。
#   G-2 `B` 必须在 step 20 左右复现 `§185` 的 `nf3` 塌陷（1169 → 个位数）。
#   G-3 若 `C ≈ B` ⇒ 我改的 `facet_excl` **不是**那个原因 ⇒ `§186` 的修法**无效**，
#       真因另有其物；若 `C ≈ A` ⇒ 修法有效。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

COMMON="--N 112 --dx-nm 62.5 --steps 40 --every 10 --snap-every 20 --pair-every 10 \
--norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
--laths 1,1,2,2,3,3,4,4,7,7,8,8 --multi-block --block-gap-nm 1300"

run_one () {
  local tag="$1"; shift
  echo "################ 臂 $tag  $(date '+%F %T')" | tee -a _r415_fpgt.log
  echo "  附加参数：$*" | tee -a _r415_fpgt.log
  timeout 3600 "$PY" -u _bk_exp.py $COMMON "$@" \
      --tag "$tag" --out _exp/_bk_mb > "_r415_${tag}.log" 2>&1
  echo "  退出码=$?  Traceback=$(grep -c Traceback "_r415_${tag}.log" || true)" \
      | tee -a _r415_fpgt.log
}

: > _r415_fpgt.log
# 三条臂**并行**跑（每条 ~1.6 GB ⇒ 合计 ~5 GB，远低于 22 GB 预算）
run_one gtA --facet-proj 0  --facet-excl 0 &
run_one gtB --facet-proj 10 --facet-excl 1 &
run_one gtC --facet-proj 10 --facet-excl 0 &
wait
echo "=== ALL ARMS DONE $(date '+%F %T') ===" | tee -a _r415_fpgt.log

# ---------- 汇总 ----------
"$PY" -u _r416_gtread.py 2>&1 | tail -60
