#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in e5_equi6 e7_selfac equi192_ns4 e7b_selfac12; do
  echo "-- $d"
  f="_exp/$d/run.log"
  if [ -f "$f" ]; then
    grep -E '变体序列|shuffle-variants|沿 w 排' "$f" | tail -2
    grep -E '^\s+\[' "$f" | tail -1 | cut -c1-135
  else
    echo "   (未启动)"
  fi
done
echo "=== procs / mem ==="
ps -eo pid,etimes,args | grep -E '_r1_exp|_r1_drive' | grep -v grep | cut -c1-60
free -g | head -2
