#!/bin/bash
# _r240_edvreal.sh —— ★ 条件③主线：在**真实 R165 几何**上量**逐变体 `ed` 分布**。
#
# ## 为什么这条是主线（`§135.6` / `§142.1`）
# `§142.1` 定量确认：**界面能项不是杠杆**（F1 比值 0.31%、F2 2–9%，
# 且 F2 只占 8.7% 面积、F3 只占 3.0%），而 `df_k − df_l ≡ 0`
# ⇒ **变体选择几乎完全由 `ed`（弹性自项）决定**
# ⇒ **"块间协调/自协调"若有，只能走 `ed` 经共享应力场这条路。**
#
# ## 要回答
# * **Q-A** `ed` 是**按变体**组织的，还是**按场/位置**组织的？
#   `_r239` 的小几何里，**同变体的两个场 `ed` 差 23%**（场1 −3.95e8 vs 场2 −4.87e8），
#   而跨变体极差只有 1.01e8 ⇒ **看起来是按场组织的**。真实几何上是不是？
#   ⇒ 判据：**`ed` 中位的"变体内离散" vs "变体间离散"** 哪个大。
# * **Q-B** 随演化，跨变体的 `ed` 极差/标准差是**变大**（分化）还是**变小**（趋同）？
# * **Q-C** 六变体的**体积**是否趋匀（`vol_cv` 下降）？—— 这是"块间协调"的直接签名。
#
# ## 单变量性
# 命令行由 `_r178_repro.py --emit` 从归档 `dry_saSet2` 逐参重建，
# **只追加 `--diag-edv`**（纯只读记账）与 `--tag`。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== 逐变体 ed 的真实几何测量开始 $(date '+%F %T') ==="
"$PY" -u _r178_repro.py saSet2 --emit > _w2_r240_emit.log 2>&1
CMD=$(grep -m1 '^    /root/miniconda3' _w2_r240_emit.log | sed 's/^ *//')
if [ -z "$CMD" ]; then echo "❌ 没抓到重建命令"; exit 1; fi
CMD=$(printf '%s' "$CMD" | sed 's/--tag [^ ]*/--tag saSet2EDV/')
CMD="$CMD --diag-edv"
echo "  ⇒ 最终命令行（只比归档多一个 \`--diag-edv\`）："
echo "     $CMD"
echo
echo "  --- 开跑 $(date '+%T') ---"
eval "$CMD" > _w2_r240_run.log 2>&1
echo "  --- 退出码 = $?  $(date '+%T') ---"
echo "=== 结束 $(date '+%F %T') ==="
