#!/bin/bash
# _r100_sascan.sh —— **6 块自协调匣子的播种几何扫描**（判据：`nf2(t=0) == 0`）。
#
# ## 为什么
# `_r98` 冒烟实测：`--plate-L 1600` + `--block-gap-nm 700/1000` 时
# **6 个块在 t=0 就大量重叠**（`nf2(t=0)` = **1845–2897** 个格面，不是 0）。
# 根因：6 个变体的 `a` 轴方向各不相同 ⇒ 块沿**布局轴 u** 排开也挡不住
# **垂直方向**的互相侵入；而"播种后质心距"只是个**粗判据**
# （`_bk_exp.py` 自己就写着"质心距只是粗判据，看下面的精确判据"）。
#
# ## 判据（**可证伪**）
#   `nf2(t=0) == 0` ⟺ 6 个块**真正分离**（`_bk_exp.py` 的"精确判据"只比块 0/块 1，
#   而 `series.csv` 的 `nf2` 覆盖**所有异变体对** ⇒ 用后者更严）。
#
# ## 扫描维度（变体集固定为**奇数集 = 每对一个**）
#   盒（N=96 ⇒ 6 µm / N=112 ⇒ 7 µm）× `--plate-L` × `--block-gap-nm`
#
# ⚠ 内存：N=96/nreg=13 ⇒ ≈2.6 GB；N=112/nreg=13 ⇒ ≈4.2 GB（§7.2c 标度律）
#   ⇒ **并发上限 4**，两批跑。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
ODD="1,1,3,3,5,5,7,7,9,9,11,11"

run() {   # run <tag> <N> <L> <W> <gap>
  local TAG="$1" NN="$2" LL="$3" WW="$4" GAP="$5"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$ODD" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 3 --tag "$TAG" --out _exp/_bk_mb > "_w2_r100_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R100 扫描开始 $(date '+%F %T')"
# 批 1：N=96 三个 + N=112 一个
run sgA 96  800 400 1000 &
run sgB 96  800 400 1200 &
run sgC 96  600 350 1400 &
run sgE 112 1600 700 1000 &
wait
echo "=== 批 1 结束 $(date '+%F %T')"
# 批 2：N=112 三个
run sgD 112 1200 600 1100 &
run sgF 112 1600 700 1200 &
run sgG 112 1000 500 1300 &
run sgH 96  1000 500 900 &
wait
echo "=== R100 扫描结束 $(date '+%F %T')"
