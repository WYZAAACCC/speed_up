#!/bin/bash
# T2.1b 并行扫描：f_eq(|df|) 曲线 + athermal 平台检验（本脚本自己 wait）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
python3 -c "import os; os.path.exists('_t21b_scan.csv') and os.remove('_t21b_scan.csv')"
$PY _t21b_scan.py 0.30 32 > _t21b_a0.30.log 2>&1 &
$PY _t21b_scan.py 0.50 32 > _t21b_a0.50.log 2>&1 &
$PY _t21b_scan.py 0.80 32 > _t21b_a0.80.log 2>&1 &
$PY _t21b_scan.py 1.20 32 > _t21b_a1.20.log 2>&1 &
$PY _t21b_scan.py 2.00 32 > _t21b_a2.00.log 2>&1 &
$PY _t21b_scan.py 3.00 32 > _t21b_a3.00.log 2>&1 &
T21B_K=120 $PY _t21b_scan.py 1.00 32 > _t21b_plat120.log 2>&1 &
T21B_K=240 $PY _t21b_scan.py 1.00 32 > _t21b_plat240.log 2>&1 &
wait
echo "=== _t21b_scan.csv ==="
cat _t21b_scan.csv
echo T21B_DONE
