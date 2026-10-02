#!/bin/bash
# _r581_f3series.sh --- ★★ goal §(17)#2/#3：用**同一把 F3 图量具**看**块的形成过程**。
#   对每个快照（step 0/200/400/600）建 3-D F3 邻接图 ⇒ 时间序列：
#     块数（F3 分量数）、链长分布、F3/F2 边数、异变体侵入事件。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 可用快照 ==='
for t in p2_b5 p2_b3; do
  printf '  %-8s ' "$t"
  ls _exp/_bk_p2/dry_$t/ 2>/dev/null | grep '^snap_' | tr '\n' ' '
  echo
done
echo
echo '=== 臂状态 ==='
bash _r581_ps.sh 2>&1 | tail -4
echo
echo '=== 逐快照的 F3 图 ==='
taskset -c 12-15 $PY _r581_f3series.py 2>&1 | tail -60
