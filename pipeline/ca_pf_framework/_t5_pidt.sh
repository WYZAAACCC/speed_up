#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== PID -> tag ==="
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*) echo "PID $P  $(echo "$C" | grep -oE '\-\-tag [A-Za-z0-9_]+|\-\-steps [0-9]+|\-\-ed-eta [0-9.]+|\-\-burst-km [0-9]+' | tr '\n' ' ')";; esac
done
echo
echo "=== _t5_ablate.sh ==="
cat _t5_ablate.sh
