#!/usr/bin/env bash
# _r556_run.sh —— **决定性单变量 A/B**：同配置下 f64 vs f32（只差 `--phi-prec`）
#
# ## 为什么要它
# `_r555` 的 `c6_b4f32`（B=4 + 周期播种 + **f32**）报出
#   `blk_nprof = [5,3,2,2,2,1,1,1,1,1,1]`
#   `blk_nruns = [5,7,3,5,2,2,2,2,3,1,2]`   ← **与 nprof 不等 ⇒ "剖面有噪声"**
# 而先前 `ps_b3`（B=3 + 周期播种 + **f64**）是
#   `blk_nprof == blk_laths == blk_nruns`（**干净**）。
#
# ⚠ **但那两者差了 TWO 个因素**（`B` 与 `phi-prec`）⇒ **不能归因**。
#   本件把 `B`、`--nuc-periodic-seed`、`--nfsv-diag` 全部固定，
#   **只差 `--phi-prec`** ⇒ 噪声是不是 f32 带来的，一次就能定。
#
# ## 预登记判据
# * **R1**：若 f32 的 `blk_nruns != blk_nprof` 而 f64 的相等 ⇒ **f32 引入了剖面噪声**（要记账）
# * **R2**：若两者**都**有噪声 ⇒ **与 f32 无关**，是 `B=4` 这个构型本身的（也要记账）
# * **R3 正对照**：两臂的 `world` 物理量（`Vt`）**可以不同**（f32 有舍入），
#   但 `R552` 已证 `region()` 逐胞相同 ⇒ 差异应**很小**（`Vt` 相对差 ≤1%）
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
nohup $PY -u _r537_parrun.py 2 _r556_preccfg.json > _w2_r556_par.log 2>&1 < /dev/null &
echo "已启动 _r556（f64 与 f32 各一臂，2 并发 × 各 4 线程）"
