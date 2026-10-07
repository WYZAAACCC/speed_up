#!/bin/bash
# _r280_r165proj0.sh —— ★★ **`§144` 的第二个 P0 跟进**：R165 在 `--facet-proj 0` 下重跑。
#
# ## 要回答什么
# R165 实测：把 F2（异变体）最便宜那几对的界面能降 **9.3 倍**，`r_selfac` 只动 **0.03%**。
# `§145.3` 给了三条叠加的解释：
#   ① `--facet-proj 10` 压制界面能对形态的影响（`§144`/`§147`）
#   ② F2 只占总界面面积的 **8.7%**（`§142.1`）
#   ③ F2 上界面能项本身只占 `|Δed|` 的 **2–9%**（`§141.1`）
#
# **本实验**：把 **①** 去掉（`--facet-proj 10 → 0`），其余**逐字不动**。
# * 若效应**仍然≈0** ⇒ **②③ 是约束**，①不是主因；
# * 若效应**显著变大** ⇒ **① 是主因**（`§144` 的归因成立）。
# ⇒ **两种结果都有信息量，都必须如实报。**
#
# ## 设计（**单变量**：只改 `--facet-proj`）
# 命令行由 `_r178_repro.py --emit` 从归档 `dry_saSet2` / `dry_saSet2F2` **逐参重建**，
# 本脚本只做两处替换：`--facet-proj 10 → 0`、`--tag`（写独立目录），
# 并**追加 `--diag-terms`**（拿到三项量级，看界面能项在无投影时是否变"活"）。
#
# ## 预登记判据（**先写死**）
# * **R-1** 前置：两臂输出目录不同；`--facet-proj` 确实为 0；γ_F2 表仍与归档一致（λ 未变）。
# * **R-2** ★ **核心**：`saSet2P0` vs `saSet2F2P0` 的 **`r_selfac` 末态相对差**，
#   与归档（`saSet2` vs `saSet2F2`）的 **−2.72e-04** 比。
#   **判据：若新相对差 ≫ 2.72e-04（≥10 倍）⇒ ① 是主因。**
# * **R-3** `--diag-terms` 的三项：无投影时 F2 的 `|stk·κ|/|Δed|` 是否比归档时更大。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_mb/dry_saSet2P0 _exp/_bk_mb/dry_saSet2F2P0

echo "=== R165 × --facet-proj 0 开始 $(date '+%F %T') ==="
PIDS=""
for SRC in saSet2 saSet2F2; do
  TGT="${SRC}P0"
  "$PY" -u _r178_repro.py "$SRC" --emit > "_w2_r280_${SRC}_emit.log" 2>&1
  CMD=$(grep -m1 '^    /root/miniconda3' "_w2_r280_${SRC}_emit.log" | sed 's/^ *//')
  if [ -z "$CMD" ]; then echo "  ❌ $SRC 没抓到重建命令"; continue; fi
  # ① 换 tag；② facet-proj 10 -> 0；③ 追加 --diag-terms
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TGT}/")
  if printf '%s' "$CMD" | grep -q -- '--facet-proj 10'; then
    CMD=$(printf '%s' "$CMD" | sed 's/--facet-proj 10/--facet-proj 0/')
  elif printf '%s' "$CMD" | grep -q -- '--facet-proj 0'; then
    echo "  ⚠ $SRC 重建命令里已经是 0"
  else
    echo "  ⚠ $SRC 重建命令里**没有** --facet-proj（会取默认 0）"
  fi
  case "$CMD" in *"--diag-terms"*) ;; *) CMD="$CMD --diag-terms" ;; esac
  echo
  echo "  --- 臂 $TGT 最终命令行（token $(printf '%s' "$CMD" | wc -w)）---"
  printf '     %s\n' "$CMD"
  printf '%s' "$CMD" | grep -q -- '--facet-proj 0' || echo "     ❌ **未成功改成 0！**"
  printf '%s' "$CMD" | grep -q -- "--tag ${TGT}" || echo "     ❌ **tag 不对！**"
  eval "$CMD" > "_w2_r280_${TGT}_run.log" 2>&1 &
  PIDS="$PIDS $!"
  echo "  ⇒ 启动 PID=$! $(date '+%T')"
done
echo
echo "  并行 PID：$PIDS"
for p in $PIDS; do wait "$p"; echo "  pid=$p 退出码 $?"; done
echo "=== 结束 $(date '+%F %T') ==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  [ -f "$f" ] && printf '  %-34s Traceback=%s\n' "$f" "$(grep -c Traceback "$f" || true)"
done
