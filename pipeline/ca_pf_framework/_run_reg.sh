#!/bin/bash
# 全量回归（本轮修完 advance 的带掩模/规范形速度后必须重跑）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for s in _chk_s1.py _chk_d4.py _chk_w2.py _chk_a3.py _chk_w1.py _chk_p1.py; do
  echo "=================== $s ==================="
  $PY -u $s 2>&1 | grep -v Warning
done
echo "=================== _chk_h6.py ==================="
$PY -u _chk_h6.py 2>&1 | grep -v Warning | tail -25
echo "=================== _chk_h7.py ==================="
$PY -u _chk_h7.py 2>&1 | grep -v Warning | tail -25
echo "=================== _chk_drag.py ==================="
$PY -u _chk_drag.py 2>&1 | grep -v Warning | tail -25
echo ALLDONE