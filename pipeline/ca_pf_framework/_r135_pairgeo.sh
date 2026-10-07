#!/bin/bash
# _r135_pairgeo.sh —— **PAIR 集（不可自协调对照）在 ODD 已通过的几何上能否放下？**
#
# ## 为什么
# 自协调三臂（`saPair` / `saPairE0` / `saOdd`）要**同几何**才干净。
# ODD 集已有多个可用几何（`_r102`/`_r121`）：
#   * `sgG`               N=112 L=1000 W=500 T=510 gap=1300  `nf2(0)=0`
#   * `t1N112L800`        N=112 L=800  W=600 T=635 gap=1200  `nf2(0)=0`
#   * `t3N128L1000`       N=128 L=1000 W=600 T=635 gap=1300  `nf2(0)=0`
#   * `t1N96L800` 等（`nf2(0)>0`，不可用）
#
# 而 PAIR 集 `{1..6}` 的**布局轴 `u = [0,1,0]`**（一条直线沿 y，直线度 0.276）
# ⇒ 比 ODD 集难放得多（`_r103` 实测在 `sgG` 几何上被引擎拒绝：
#   `ValueError: elongated seed exceeds domain`）。
#
# ⇒ 本脚本把 PAIR 集放到上面三个几何上，判据仍是 **`nf2(t=0) == 0`**。
#   若有一个过 ⇒ 三臂可**同几何**跑；都没有 ⇒ 只能用各自的几何并**显式记账**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PAIR="1,1,2,2,3,3,4,4,5,5,6,6"

run() {   # run <tag> <N> <L> <W> <T> <gap>
  local TAG="$1" NN="$2" LL="$3" WW="$4" TT="$5" GAP="$6"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T "$TT" --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$PAIR" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 2 --tag "$TAG" --out _exp/_bk_mb > "_w2_r135_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R135 PAIR 集几何测试开始 $(date '+%F %T')"
run pA 112 800  600 635 1200 &
run pB 128 1000 600 635 1300 &
run pC 112 1000 500 510 1200 &
run pD 112 800  600 635 1000 &
wait
echo "=== 批 1 结束 $(date '+%F %T')"
run pE 128 1000 600 635 1100 &
run pF 112 1000 500 510 1000 &
wait
echo "=== R135 结束 $(date '+%F %T')"
