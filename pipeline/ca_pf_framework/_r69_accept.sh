#!/bin/bash
# _r69_accept.sh —— **面片投影的验收臂**（判据先写死）
#
# ## 背景
# `R30_AUDIT_LEDGER.md` §65：算子 `_r68_facet_op` 已过正对照
#   （解析长方体幂等 `s=1.000`、体积 0.0%；真实圆化快照 `f_flat` 0.005 → 0.155）。
# `BLOCK_SELFAC.md §8`：源起是"平坦端面在 ~5Δx 行程内必丢"（三来源全排除）。
#
# ## 判据（**先写死**）
#   F-1 **`f_flat` 在 step 400 仍 ≥0.10**（对照：不开时 0.005）—— 第一验收线
#   F-2 `v_a/v_w` 从 ~1.6 提到 **≥3**（第二线；理论上限 8.93）—— 宽松设阈，
#       因为"投影+平流交替"的净效果未知
#   F-3 体积守恒：`Vt` 的轨迹与不开时同量级（投影不该改变增长量级）
#   F-4 `box_touch_core == 0`
#   F-5 ⚠ 若 F-1 过而 F-2 不过 ⇒ 说明"面恢复了但形状仍不各向异性"，
#       那是**另一层**问题（速度律的空间分布），需另立条目
#
# 配置与 `_r54_single.sh` 逐项相同（单板条、N=64、Δx=62.5、400 步），只差 `--facet-proj`。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 面片投影验收  $(date '+%F %T')"
for SPEC in "fp20:20" "fp0:0"; do
  TAG="${SPEC%%:*}"; NP="${SPEC#*:}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  facet_proj=$NP  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj "$NP" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r69_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== 完成 $(date '+%F %T')"
