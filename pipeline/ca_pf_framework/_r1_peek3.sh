#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in mid250_base mid250_noel mid250_ns2 lath1 mid1; do
  echo "### $d"
  if [ -f "_exp/$d/run.log" ]; then
    tail -4 "_exp/$d/run.log"
    echo "   rows=$(wc -l < _exp/$d/series.csv 2>/dev/null)"
  else
    echo "   (no log)"
  fi
  echo
done
echo "### procs"
ps -eo pid,etimes,pcpu,rss,args --sort=-rss | head -8 | cut -c1-140
echo "### mem"; free -g | head -2
