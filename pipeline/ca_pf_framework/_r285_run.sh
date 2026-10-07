#!/bin/bash
# _r285_run.sh —— 一次跑完：摘要更新 + P1-45（投影组，**已跑满 400 步**）判决 + 状态。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

echo "################ ① 摘要更新（§153）################"
"$PY" -u _r283_summary7.py 2>&1 | tail -2

echo
echo "################ ② **P1-45 投影组末态判决（O-2）** ################"
"$PY" -u _r243_p45sign.py 2>&1 | tail -40
