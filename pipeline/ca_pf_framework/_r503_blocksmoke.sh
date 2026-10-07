#!/usr/bin/env bash
# R503 —— `--nuc-block-target`（"块数"口径）的**预登记验收**。
#
# 规范见 `R502_BLOCKCOUNT.md`（§5 实现规范、§6 判据 B1–B4）。
#
# 判据（**先写死**）：
#   B1【默认惰性】`B=0` ⇒ 与旧路径**同读数**（真正的逐位回归由 `_r30_regress.sh` 另跑）
#   B2【总量真放开】`B=8` 的事件数**必须 > `B=0` 的事件数**
#   B3【几何上界守卫】`B=100`（> `B_max`）⇒ **必须**打出超界告警（**反向测守卫**）
#   B4【B=1 退化】`B=1` 与 `B=0` 的事件数**必须相同**（证明 `B·n` 在 `B=1` 退化为 `n`）
#
# 配置：`N=48`（L=3 µm ⇒ `B_max = 9/0.5 = 18`）、不开超临界（让旧放置规则主导）、
#       `--nuc-max-per-step 4`（不然一步只放 1 个，测不出总量差别）。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=6
STEPS=1200
# 48 个场：12 变体 × 4 场 ⇒ 足够装下 B=8 时的多块多根
LATHS="1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8,8,8,8,9,9,9,9,10,10,10,10,11,11,11,11,12,12,12,12"
COMMON="--N 48 --dx-nm 62.5 --every 10 --snap-every 99999 --phi-band-every 99999 \
 --pair-every 0 --norm-smooth 0 --nthreads $NT --laths $LATHS \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 4 --nuc-fresh-every 22 \
 --nuc-max-per-step 4 --alpha-km 0.041739 --T-end 500.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
 --steps $STEPS --out $OUT"

run_arm () {
  local TAG="$1"; shift
  echo "== 臂 $TAG   $(date '+%F %T')"
  local T0=$(date +%s)
  $PY -u _bk_exp.py $COMMON "$@" --tag "$TAG" > "_w2_r503_${TAG}.log" 2>&1
  echo "臂 $TAG 退出码=$?  用时 $(( $(date +%s) - T0 )) s"
}

run_arm r503B0 --nuc-block-target 0   &
P0=$!
run_arm r503B1 --nuc-block-target 1   &
P1=$!
run_arm r503B8 --nuc-block-target 8   &
P8=$!
run_arm r503BIG --nuc-block-target 100 &
PB=$!
wait $P0; wait $P1; wait $P8; wait $PB
echo "四臂结束 $(date '+%F %T')"
echo
$PY -u _r503_blockverdict.py
