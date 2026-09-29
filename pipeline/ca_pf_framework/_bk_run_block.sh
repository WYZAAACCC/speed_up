#!/bin/bash
# _bk_run_block.sh —— 启动阶段 3 的生产臂（后台、绝对日志、带 tag 不覆盖）
#   用法: bash _bk_run_block.sh <tag> <arm1> <arm2> ...
#
# ★★ 2026-09-29 教训（本轮 WSL 崩过一次：`Wsl/Service/E_UNEXPECTED`）：
#   两个 N=192/7 场算例的 RSS 涨到 **9.3 GB/个**（工作集其实只有 ~1 GB）
#   ⇒ 24 GB 的 VM 被吃满 ⇒ 3 GB 可用 ⇒ 算例变慢 ⇒ 最终 WSL 服务级故障。
#   根因是 **glibc malloc 的 arena 保留**：numpy 反复申请/释放 56–400 MB 的
#   N³ 临时数组时，内存**不还给 OS**，RSS 只涨不落。
#   ⇒ 解法：`MALLOC_MMAP_THRESHOLD_` 调小 ⇒ 大块走 mmap ⇒ free 时**真的归还**；
#           `MALLOC_TRIM_THRESHOLD_` 调小 ⇒ 堆顶及时 trim。
#   ⚠ 这两个变量**只影响内存管理，不影响任何数值**（判据：同算例逐位相同）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
export MALLOC_MMAP_THRESHOLD_=65536
export MALLOC_TRIM_THRESHOLD_=65536
export MALLOC_ARENA_MAX=2
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
