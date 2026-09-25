#!/bin/bash
# 全量回归（2026-09-25 起含 M2 判据）—— 任何改动后**必须**重跑
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for s in _chk_s1.py _chk_d4.py _chk_w2.py _chk_a3.py _chk_w1.py _chk_p1.py _chk_pf.py; do
  echo "=================== $s ==================="
  $PY -u $s 2>&1 | grep -v Warning
done
echo "=================== _chk_hex.py (各向异性弹性张量) ==================="
$PY -u _chk_hex.py 2>&1 | grep -v Warning | grep -E 'PASS|FAIL|HX 总判定'
echo "=================== _chk_aniso.py (不均匀价值门槛) ==================="
$PY -u _chk_aniso.py 2>&1 | grep -v Warning | grep -E '⇒|AV-'
echo "=================== _chk_as.py (inhomogeneous 弹性求解器) ==================="
$PY -u _chk_as.py 2>&1 | grep -v Warning | grep -E 'PASS|FAIL|AS 总判定|记账|E_inh'
echo "=================== _chk_irf.py (V8-a: CA 的 LKT 表独立核对) ==================="
$PY -u _chk_irf.py 2>&1 | grep -v Warning | grep -E '表:|全表|参照|⇒'
echo "=================== _chk_thermo.py (F1/F2 文献+理论闭合) ==================="
$PY -u _chk_thermo.py 2>&1 | grep -v Warning | grep -E '=>|dT0 目标|k\*|⇒|实测'
echo "=================== _chk_irf2.py (ΔT_0 对 Window A 的影响) ==================="
$PY -u _chk_irf2.py 2>&1 | grep -v Warning | grep -E 'B0|工作点|12|23|Vc|Vc|可用的|=>'
echo "=================== _chk_m2c.py 32 20 ==================="
$PY -u _chk_m2c.py 32 20 2>&1 | grep -v Warning | grep -E 'M2-|带健康|法向 vs|S_v|末态|===='
for s in _chk_h6.py _chk_h7.py _chk_drag.py; do
  echo "=================== $s ==================="
  $PY -u $s 2>&1 | grep -v Warning | tail -22
done
echo ALLDONE
