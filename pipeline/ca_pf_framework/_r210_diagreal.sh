#!/bin/bash
# _r210_diagreal.sh —— ★ `§135.7` 的**决定性检验**：在 **R165 的真实几何**上量三项占比。
#
# ## 为什么必须用真实几何
# `_r208` 的接线测试是 N=32 / `1,1,2,2` / 6 步 —— 只够验接线。
# 它已经显示**三类界面的比值差 100 倍**（F1 0.43% / F2 39.6% / F3 分母为 0）
# ⇒ **绝不能用"全局中位"代表全部**（`§135.5` 就是这么错的）。
#
# ## 要回答
# * **Q-A** 三类界面的**面积占比**（`series.csv` **没有** `f1_area` 列 ⇒ 只能用本诊断的胞数）
# * **Q-B** F2 的比值中位到底多少？⇒ 若 ~40%，R165 的否定结果就**需要新解释**
# * **Q-C** F3 的 `Δed ≡ 0` 是否全程成立？（若成立 ⇒ **块内界面运动完全由界面能控制**）
#
# ## 单变量性
# 命令行由 `_r178_repro.py --emit` 从归档 `exp_args` **逐参重建**，
# 本脚本**只追加** `--diag-terms`（纯记账、不改数值）与 `--tag`（写独立目录）。
# ⚠ 不走 `--set`（`_r178` 的 `--set` 解析在本机上吞参数，已记账）——
#   改成**捕获重建结果再追加**，并把**最终命令行完整打印**出来以便核对。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== 决定性检验开始 $(date '+%F %T') ==="

for TAG in saSet2 saOddG; do
  echo
  echo "########## 臂 $TAG ##########"
  # ① 取重建出的命令行（`--emit` 只打印不执行）
  "$PY" -u _r178_repro.py "$TAG" --emit > "_w2_r210_${TAG}_emit.log" 2>&1
  CMD=$(grep -m1 '^    /root/miniconda3' "_w2_r210_${TAG}_emit.log" | sed 's/^ *//')
  if [ -z "$CMD" ]; then
    echo "  ❌ 没抓到重建命令，见 _w2_r210_${TAG}_emit.log"; continue
  fi
  # ② 把 tag 换成独立目录名，并追加 --diag-terms（纯记账）
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}DT/")
  CMD="$CMD --diag-terms"
  echo "  ⇒ 最终命令行（token 数 $(printf '%s' "$CMD" | wc -w)）："
  echo "     $CMD"
  echo "  ⚠ 只比归档多 **一个** `--diag-terms`；`--tag` 只决定写到哪个目录。"
  echo
  echo "  --- 开跑 $(date '+%T') ---"
  eval "$CMD" > "_w2_r210_${TAG}_run.log" 2>&1
  echo "  --- $TAG 退出码 = $?  $(date '+%T') ---"
done
echo
echo "=== 结束 $(date '+%F %T') ==="
