#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== procs ==="
ps -eo pid,etimes,args | grep -E '_r1_exp|_r1_drive' | grep -v grep | cut -c1-78
echo "=== mem ==="; free -g
echo "=== tails ==="
for d in e4_lath6 e6_mid6 e5_equi6 e7_selfac equi192_ns4 e7b_selfac12; do
  f="_exp/$d/run.log"
  if [ -f "$f" ]; then
    echo "$d : $(grep -E '^\s+\[' "$f" | tail -1 | cut -c1-108)"
  else
    echo "$d : (未启动)"
  fi
done
