#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py; do
  echo "### $f"
  start=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > /tmp/base_$f.log 2>&1
  rc=$?
  echo "  rc=$rc  wall=$(( $(date +%s) - start )) s"
  tail -4 /tmp/base_$f.log
done