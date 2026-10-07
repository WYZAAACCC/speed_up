#!/bin/bash
# _r54_single.sh —— **单根孤立板条**的成形对照（`pin_min=True`，即真实板条配置）
#
# ## 为什么这是当前最该跑的一条（`R30_AUDIT_LEDGER.md` §39 + 引擎自己的注释）
# 引擎注释原文（`windowB_surface.py:3363`）：
#   「⚠ 记账：D8 的 a00..a100 用的是 **pin_min=False**（当时 mref = 快生长方向），
#     所以它给的是"沿 mref 拉长"；那组数据证明的是**机制有效**（主轴 0.0 deg、
#     长径比单调 1.00->2.15），**不是"板条已得到"**。板条要用 pin_min=True + n*=惯习面法向。」
# ⇒ **`pin_min=True` 从来没有过受控的单核验证。**
# 而 §38 实测：多板条构型下 `v_a/v_w` 只有 1.24–1.48（做出 9:1 板条需要 ≳12）。
#
# ## 这条臂要回答什么（**判据先写死**）
#   S-1 **单根**孤立板条（无邻居 ⇒ 排除多体弹性相互作用）在 `pin_min=True` 下，
#       长径比 `L/W` 是否**上升**？（v2 口径，正对照已证速率误差 <0.5%）
#   S-2 `v_a/v_w`（由 v2 口径的 `d(a)`/`d(w)` 给出）是否显著大于 1？
#   S-3 与解析预期对照：`M(a)/M(w) = exp(-β_h·0.127²)/exp(-β_w) = %.2f`
#       ⇒ 若实测远低于此 ⇒ **不是迁移率的问题，是别的东西在压**。
#   S-4 厚度 `d(n)` 是否被钉住（`pin_min=True` 且 `mob_beta_w>0` 的核心目的）。
#
# ## 成本（实测标度律）
#   `N³·nreg/1e6 = 64³×2/1e6 = 0.52` ⇒ ≈0.3 秒/步、≈0.12 GB ⇒ 600 步 ≈ **3 分钟**
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

MODE="${1:-run}"
case "$MODE" in
  smoke) STEPS=60 ;;
  run)   STEPS=600 ;;
  *) echo "用法: $0 [smoke|run]"; exit 2 ;;
esac

TAG=single
rm -rf "_exp/_bk_mb/dry_$TAG"
echo "=== R54 $TAG 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 \
  --laths 1 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps "$STEPS" --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_r54_${TAG}.log" 2>&1
echo "=== R54 $TAG rc=$?  $(date '+%F %T')"
