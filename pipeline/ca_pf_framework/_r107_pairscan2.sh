#!/bin/bash
# _r107_pairscan2.sh —— PAIR 集（`{1..6}`，不可自协调）的**第二轮**几何扫描（更小板条）。
#
# `_r104` 实测：N=112 / L=1000 / W=500 时，gap 900/1000/1100 **全部重叠**
# （`nf2(t=0)` = 389/255/163，随间距单调降但都 > 0），
# 而 gap 1300 又把种子顶出盒壁（`ValueError: elongated seed exceeds domain`）
# ⇒ **在这个 (L,W,N) 下可用窗口是空的**。
#
# ⇒ 缩板条（L 1000→600、W 500→350）再扫。参照：`sgC`（N=96/L=600/W=350/gap=1400，
#    ODD 集）是过的，但 **PAIR 集的布局轴是 `[0,1,0]`（一条直线）**，比 ODD 集难放得多。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PAIR="1,1,2,2,3,3,4,4,5,5,6,6"

run() {   # run <tag> <N> <L> <W> <gap>
  local TAG="$1" NN="$2" LL="$3" WW="$4" GAP="$5"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T 510 --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$PAIR" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 2 --tag "$TAG" --out _exp/_bk_mb > "_w2_r107_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R107 PAIR 第二轮扫描开始 $(date '+%F %T')"
run q600g1000 112 600 350 1000 &
run q600g1200 112 600 350 1200 &
run q600g1400 112 600 350 1400 &
run q450g1200 112 450 300 1200 &
wait
echo "=== R107 结束 $(date '+%F %T')"
