#!/bin/bash
# _r314_verdicts.sh —— 一次跑完三个判决（**都在终点之后**）：
#   ① Z-2 窄口径（`f3_area` 逐 step 模式，投影 vs 无投影，**共同步到 400**）
#   ② Z-2 宽口径（全部 95 列）
#   ③ `§146` 的**第二构型**检验（`mb2fp10EDV`：2 块 × 3 根 / 2 变体）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "################ ① Z-2 窄口径（f3_area 逐 step）################"
"$PY" -u _r286_z2f3.py 2>&1 | tail -32
echo
echo "################ ② Z-2 宽口径（全部列）################"
"$PY" -u _r276_z2now.py 2>&1 | tail -30
echo
echo "################ ③ §146 第二构型（mb2fp10EDV）################"
"$PY" -u _r313_edv2read.py 2>&1 | tail -30
