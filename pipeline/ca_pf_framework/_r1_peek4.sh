#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== live R24 runs ==="
for d in mid192_ns4 lath192_ns4; do
  echo "--- $d  rows=$(wc -l < _exp/$d/series.csv 2>/dev/null)"
  grep -E '^\s+\[' "_exp/$d/run.log" 2>/dev/null | tail -2
done
echo
echo "=== procs ==="
ps -eo pid,etimes,pcpu,rss,args --sort=-rss | head -6 | cut -c1-120
echo "=== mem ==="; free -g | head -2
