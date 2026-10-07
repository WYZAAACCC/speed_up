#!/bin/bash
# _r61_accept.sh —— **刻面机制的验收臂**（P1-31 的实现，判据先写死）
#
# ## 背景
# §45：单根孤立板条实测 `v_a/v_w` = **1.6–2.0**（三种平流格式都一样），
#      而"刻面演化"的解析预言是 **9.9**（§42）；§46/§47 给出机制与实现，
#      §47 的自检：`c=4` ⇒ `h(a)/h(w)` = **9.73**（3D）。
#
# ## 判据（**先写死，跑完照此判**）
#   W-1 **主判据**：`--mob-wulff --mob-dip 4` 的 `v_a/v_w`（v2 口径）**≥ 6**
#       （对照：关掉时 1.6–2.0；解析目标 9.73）
#   W-2 `d(n)/d(a)` 保持很小（厚度钉扎；关闭时 ≈0.033）
#   W-3 `box_touch_core == 0` 全程（没撞壁）
#   W-4 ⚠ 若 `W-1` 不过：**不得**直接下"机制无用"的结论 ——
#       必须先查 `--mob-dip` 是否真的改变了 `Mfac`（加一行打印核对）
#
# ## 配置（与 `_r54_single.sh` 逐项相同，**只差两个新开关**）
#   单根孤立板条、N=64、Δx=62.5（`t/Δx = 10.16`）、400 步
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "=== 刻面验收  $(date '+%F %T')"
for SPEC in "wulff_c4:--mob-wulff --mob-dip 4" "wulff_c0:--mob-wulff" "wulff_off:"; do
  TAG="${SPEC%%:*}"; FLAGS="${SPEC#*:}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  flags='$FLAGS'  $(date '+%T')"
  # shellcheck disable=SC2086
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    $FLAGS \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r61_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== 全部完成 $(date '+%F %T')"
