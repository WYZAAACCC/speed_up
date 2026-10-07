#!/bin/bash
# _r98_sasmoke.sh —— **6 块"每对一个"自协调匣子**的**播种几何冒烟**（只跑 20 步）。
#
# ## 为什么先冒烟
# `_r88/_r94` 定了：自协调要求变体集**每个配对取一个**
#   配对 = (1,2) (3,4) (5,6) (7,8) (9,10) (11,12)
# ⇒ 奇数集 {1,3,5,7,9,11} 与偶数集 {2,4,6,8,10,12} **都在**那 64 个六元组里。
#
# ⚠ **6 个块在一个 6 µm 周期盒里很可能播种就重叠**（R31/R51 已经为 2 块踩过这个坑：
#   布局轴 = `Σ a_b` 归一化，6 个 `a` 可能几乎抵消 ⇒ 块心挤在一起）。
# ⇒ **先只跑 20 步**，读 **step 0 的 `nf2`**（异变体接触格面数）：
#      `nf2(t=0) == 0` ⟺ 6 个块**真正分离**（可证伪的判据，不是"看着像"）。
#
# ## 扫的变量
#   ① `--block-gap-nm`：700 / 1000 / 1300 nm
#   ② 变体集：奇数（{1,3,5,7,9,11}）/ 偶数（{2,4,6,8,10,12}）
#
# 其余逐项相同（N=96 / Δx=62.5 nm / 盒 6 µm / 12 根 / `--facet-proj 10`）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

ODD="1,1,3,3,5,5,7,7,9,9,11,11"
EVEN="2,2,4,4,6,6,8,8,10,10,12,12"

run() {   # run <tag> <laths> <gap>
  local TAG="$1" LATHS="$2" GAP="$3"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
    --plate-L 1600 --plate-W 700 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LATHS" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb > "_w2_r98_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R98 播种冒烟开始 $(date '+%F %T')"
run saOdd700  "$ODD"  700  &
run saOdd1000 "$ODD" 1000  &
run saEven700 "$EVEN" 700  &
run saEven1000 "$EVEN" 1000 &
wait
echo "=== R98 冒烟结束 $(date '+%F %T')"
