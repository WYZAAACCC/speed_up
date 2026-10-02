#!/bin/bash
# _r581_f3run.sh --- 对两个臂跑 F3 邻接图（3-D 口径的 C3）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for t in p2_b5 p2_b3; do
  echo "############################ $t"
  taskset -c 12-15 $PY _r581_f3graph.py "$t" 2>&1 | sed -n '/F3 连通分量/,/^   ⇒/p'
  echo
done
