#!/bin/bash
# _r56_band.sh —— **P1-31 的定位实验**：扫速度扩展带宽，看 `v_a/v_w` 动不动。
#
# ## 背景（`R30_AUDIT_LEDGER.md` §42）
# 解析（2D 支撑函数/Huygens，同一个 `M(n)`）给 **`v_a/v_w = 9.90`**（自校验：`v_w` 逐位吻合），
# 而引擎实测（`dry_single`，单根孤立板条，v2 口径）只有 **1.24**。
# 首要嫌疑 = 速度扩展带宽（引擎注释自己写过"带太窄 ⇒ 有效速度塌"，
# 但那条对照是**各向同性**的，看不到角各向异性）。
#
# ## 判据（先写死）
#   B-1 若某个带宽能把 `v_a/v_w` 从 1.24 抬到 **≥6** ⇒ **P1-31 定位成功**（数值问题）
#   B-2 若 5→40 胞全扫都在 1.2 附近 ⇒ **不是带宽**，转向平流格式/延拓/凸包缺失
#   B-3 ⚠ 同时看 `d(n)`（厚度钉扎）与 `box_touch_core`，确认没把别的东西改坏
#
# 配置与 `_r54_single.sh` 逐项相同（单根孤立板条），**只差 `--band-cells`**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

$PY -c "import ast;ast.parse(open('_bk_exp.py').read())" || { echo SYNTAX-FAIL; exit 1; }
echo "SYNTAX-OK  $(date '+%F %T')"

for BC in 5 10 20 40; do
  TAG="bc${BC}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "=== band_cells=$BC  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --band-cells "$BC" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r56_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== 全部完成 $(date '+%F %T')"
