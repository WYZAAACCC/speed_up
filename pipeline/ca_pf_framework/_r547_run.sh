#!/usr/bin/env bash
# _r547_run.sh —— ① B=8 + 周期播种（取 `fresh` 归因 N14）② **回归**：B=4 默认（应逐位复现归档 `b4`）
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
nohup $PY -u _r537_parrun.py 2 _r547_frcfg.json > _w2_r547_par.log 2>&1 < /dev/null &
echo "已启动 `_r547`（2 并发 × 各 4 线程）"
