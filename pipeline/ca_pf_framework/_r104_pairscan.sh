#!/bin/bash
# _r104_pairscan.sh —— **PAIR 集**（`{1..6}`）的播种几何扫描。
#
# ## 为什么单独扫
# `_r103` 实测：`--laths 1,1,2,2,3,3,4,4,5,5,6,6` 的**布局轴 `u = [0,1,0]`**
# ⇒ 6 个块**沿 y 排成一条直线**，间距 1300 nm ⇒ 最外侧块心只离壁 250 nm，
# 而板条沿 `a` 的半长 500 nm（`elong=2`、`R=500`）
# ⇒ 引擎**显式拒绝**：
#     `ValueError: elongated seed exceeds domain: elong*R=5e-07 um > margin 1.372e-07 um`
# （这是**好事**：引擎没有静默把种子切掉。）
#
# ⚠ 对照：ODD 集（`{1,3,5,7,9,11}`）的 `u = [0.603, 0.721, -0.342]` ⇒ 块**斜着排**，
#    同一个 1300 nm 间距**能放下**（`sgG`：`nf2(t=0) == 0` ✅）。
#    ⇒ **两个变体集的几何**不可能完全一样（`u` 由变体的 `a` 轴决定）——
#      这必须随结论一起记账。
#
# ## 判据
#   `nf2(t=0) == 0`（覆盖**所有**异变体对）⇒ 6 块真正分离。
#   在满足它的间距里**取最大**（块离得越开，"相互影响"的信号越干净）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PAIR="1,1,2,2,3,3,4,4,5,5,6,6"

run() {   # run <tag> <gap>
  local TAG="$1" GAP="$2"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N 112 --dx-nm 62.5 \
    --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$PAIR" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 2 --tag "$TAG" --out _exp/_bk_mb > "_w2_r104_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R104 PAIR 间距扫描开始 $(date '+%F %T')"
run pg900 900 &
run pg1000 1000 &
run pg1100 1100 &
wait
echo "=== R104 结束 $(date '+%F %T')"
