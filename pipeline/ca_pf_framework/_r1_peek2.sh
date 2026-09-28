#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in lath1 mid1; do
  echo "=== $d ==="
  tail -5 "_exp/$d/run.log" 2>/dev/null
  echo "  rows: $(wc -l < _exp/$d/series.csv 2>/dev/null)  snaps: $(ls _exp/$d/snap_*.npz 2>/dev/null | wc -l)"
  echo
done
echo "=== procs ==="
ps -eo pid,etimes,pcpu,rss,args --sort=-rss | head -7 | cut -c1-150
echo "=== mem ==="
free -g | head -2
