#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
mkdir -p _audit_logs
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py verify_ca3d_wc_cet.py; do
  s=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > _audit_logs/$f.log 2>&1
  rc=$?
  echo "### $f  rc=$rc  wall=$(( $(date +%s) - s ))s"
  echo "    PASS=$(grep -c 'PASS' _audit_logs/$f.log)  FAIL=$(grep -c 'FAIL' _audit_logs/$f.log)  WARN=$(grep -c 'WARN' _audit_logs/$f.log)  JITfail=$(grep -c 'JIT compile failed' _audit_logs/$f.log)"
  grep -E '\(FAIL|\[FAIL' _audit_logs/$f.log | head -5
done
echo DONE