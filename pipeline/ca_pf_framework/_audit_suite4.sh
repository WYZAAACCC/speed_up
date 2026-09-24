#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/_audit_logs
for f in verify_ca3d.py.log verify_ca3d_solute.py.log verify_ca3d_physics.py.log; do
  echo "=== $f"
  grep -nE 'FAIL' "$f" | head -4
  echo "   (WARN:)"
  grep -nE 'WARN' "$f" | head -3
done