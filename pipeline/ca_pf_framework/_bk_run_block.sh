#!/bin/bash
# _bk_run_block.sh —— 启动阶段 3 的生产臂（后台、绝对日志、带 tag 不覆盖）
#   用法: bash _bk_run_block.sh <tag> <arm1> <arm2> ...
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
TAG=${1:?需要 tag}; shift
COMMON="--N 192 --dx-nm 62.5 --steps 200 --every 5 --snap-every 50 --norm-smooth 0 --nthreads 4 --out _exp/_bk_block"
for arm in "$@"; do
  LOG=/mnt/f/speed_up/pipeline/ca_pf_framework/_w2_blk_${arm}_${TAG}.log
  setsid nohup "$PY" -u _bk_exp.py --arm "$arm" $COMMON --tag "$TAG" \
      > "$LOG" 2>&1 < /dev/null &
  echo "started arm=$arm pid=$! log=$LOG"
  sleep 2
done
