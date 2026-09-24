#!/bin/bash
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py verify_ca3d_wc_cet.py; do
  L=/tmp/v_$f.log
  if [ -f "$L" ]; then
    echo "=== $f"
    grep -nE '\[?(FAIL|WARN)' "$L" | head -8
  else
    echo "=== $f (无日志)"
  fi
done