#!/bin/bash
# _r137_setgeo.sh —— **换"不可自协调"对照集**：`{1,2,3,4,7,8}`（`_r108` 挑出来的）。
#
# ## 为什么换
# `_r135` 实测：**PAIR 集 `{1..6}` 在 ODD 集已通过的全部 6 个几何上都放不下**
# （2 个崩：`ValueError: elongated seed exceeds domain`；4 个块间重叠 `nf2(0)=177–403`）。
# 根因：`{1..6}` 的**布局轴 `u = normalize(Σ a_v) = [0,1,0]`**（6 个 `a` 几乎同向
# ⇒ **一条直线沿 y**，直线度 **0.276**）⇒ 间距小则重叠、间距大则顶出盒壁，**窗口是空的**。
#
# ## 备选集从哪来（`_r108_cand.py`，遍历全部 `C(12,6)=924`）
# **`{1,2,3,4,7,8}`**：`r_min` **同为 0.4828**（不可自协调，与 `{1..6}` 等价），
# 但**直线度只有 0.013**（`Σa` 几乎抵消 ⇒ 布局轴与各 `a` 近乎垂直 ⇒ 好放）。
#
# ## 判据
# `nf2(t=0) == 0`（覆盖**所有**异变体对）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
# `{1,2,3,4,7,8}`，每块 2 根
S2="1,1,2,2,3,3,4,4,7,7,8,8"

run() {   # run <tag> <N> <L> <W> <T> <gap>
  local TAG="$1" NN="$2" LL="$3" WW="$4" TT="$5" GAP="$6"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T "$TT" --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$S2" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 20 --every 20 --snap-every 20 --pair-every 20 \
    --nthreads 2 --tag "$TAG" --out _exp/_bk_mb > "_w2_r137_${TAG}.log" 2>&1
  echo "  done $TAG rc=$?"
}

echo "=== R137 集2 几何测试开始 $(date '+%F %T')"
run s2a 112 1000 500 510 1300 &      # sgG 几何
run s2b 112 800  600 635 1200 &      # t1N112L800 几何
run s2c 128 1000 600 635 1300 &      # t3N128L1000 几何
run s2d 112 800  600 635 1000 &
wait
echo "=== 批 1 结束 $(date '+%F %T')"
run s2e 112 1000 500 510 1000 &
run s2f 128 800  600 635 1300 &
wait
echo "=== R137 结束 $(date '+%F %T')"
