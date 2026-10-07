#!/bin/bash
# _r179_inert.sh —— **W-1 惰性复现**（`§129`）。
#
# ## 要证什么
# `dry_saSet2F2`(λ=1) 与 `dry_saSet2`(λ=0) 的**代码 SHA 不同**（本轮改过
# `_bk_exp.py` / `windowB_lath.py` / `_bk_measure.py`）⇒ "代码变了"是混杂因素。
# **⇒ 必须用新代码 + λ=0 重跑，与归档逐位对比。**
#
# ## 判据（**先写死**）
# * **I-1** 新跑（`saSet2INERT`，120 步）与归档 `dry_saSet2` 的**前 7 行
#   （step 0,20,…,120）逐位相同**（`repr(float)` 完全一致）。
#   ⇒ 逐位相同 ⇒ **代码改动对 λ=0 路径完全惰性** ⇒ R165 是合法单变量对照。
# * **I-2** 若不同，**先看差异量级**：落在 `1e-12` 相对量级 ⇒ 只是求和次序
#   （`§92` 的 T3 gather 路径那种，属可接受）；落在 O(1) ⇒ **真混杂，R165 判决作废**。
# * **I-3** 元数据里的 `nthreads` 保持 **3**（与归档一致）—— 不要为了快改成 4，
#   那会**引入第二个变量**。
#
# ## 设计（**单变量**）
# 命令行由 `_r178_repro.py` 从归档 meta 的 `exp_args` **逐参重建**，
# 只覆盖三处：`tag=saSet2INERT`（写到独立目录，不碰归档）、`steps=120`（省时）、
# `out=_exp/_bk_mb`。**不传 `--f2-pair-gamma`** ⇒ 默认 0.0 ⇒ 应与归档同路径。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== W-1 惰性复现开始 $(date '+%F %T') ==="
echo "--- 重建并执行（新代码 + λ=0 + 120 步）---"
"$PY" -u _r178_repro.py saSet2 --set tag=saSet2INERT steps=120 out=_exp/_bk_mb \
  2>&1 | tail -40
echo "--- 退出码 ${PIPESTATUS[0]} ---"
echo "=== 结束 $(date '+%F %T') ==="
