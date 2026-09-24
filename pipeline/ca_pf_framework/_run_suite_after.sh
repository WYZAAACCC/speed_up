#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
rm -rf _audit_logs/after_fix1; mkdir -p _audit_logs/after_fix1
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py verify_ca3d_wc_cet.py; do
  s=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > _audit_logs/after_fix1/$f.log 2>&1
  echo "$f rc=$? wall=$(( $(date +%s) - s ))s  $(grep -h '汇总' _audit_logs/after_fix1/$f.log | tail -1)"
done
echo SUITE_DONE