#!/usr/bin/env bash
# _r542_readb.sh —— 读 `_r541` 并行跑出来的 B=4 / B=3 两臂的预登记判据
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
for t in b4 b3; do
  echo "##################### $t #####################"
  $PY -u _r540_b5verdict.py "$t" _exp/_bk_par 2>&1 | tail -16
  echo
done
