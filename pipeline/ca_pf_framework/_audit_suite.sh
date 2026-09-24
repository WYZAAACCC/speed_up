#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py verify_ca3d_wc_cet.py; do
  s=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > /tmp/v_$f.log 2>&1
  rc=$?
  echo "### $f  rc=$rc  wall=$(( $(date +%s) - s ))s"
  echo "    PASS=$(grep -c 'PASS' /tmp/v_$f.log) FAIL=$(grep -c 'FAIL' /tmp/v_$f.log) WARN=$(grep -c 'WARN' /tmp/v_$f.log) JITfail=$(grep -c 'JIT compile failed' /tmp/v_$f.log)"
  grep -E '^\[?(FAIL|WARN)' /tmp/v_$f.log | head -6
done