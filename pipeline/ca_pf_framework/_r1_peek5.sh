#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in e4_lath6 e6_mid6; do
  echo "=== $d ==="
  if [ -f "_exp/$d/run.log" ]; then
    grep -E '沿 w|播种|种子实测|★块：|^  \[' "_exp/$d/run.log" | tail -4
    echo "   rows=$(wc -l < _exp/$d/series.csv 2>/dev/null)"
  else
    echo "  (no log yet)"
  fi
  echo
done
echo "=== procs ==="
ps -eo pid,etimes,pcpu,rss,args --sort=-rss | head -5 | cut -c1-110
echo "=== mem ==="; free -g | head -2
