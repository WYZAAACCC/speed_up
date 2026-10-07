#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in e4_lath6 e6_mid6; do
  echo "-- $d (rows=$(wc -l < _exp/$d/series.csv 2>/dev/null))"
  grep -E '^\s+\[' "_exp/$d/run.log" 2>/dev/null | tail -1
done
echo "=== components.csv 尾部 ==="
for d in e4_lath6 e6_mid6; do
  echo "-- $d"
  tail -3 "_exp/$d/components.csv" 2>/dev/null || echo "   (尚未生成，跑 _r1_snapinfo.py --series)"
done
echo "=== mem ==="; free -g | head -2
ps -eo pid,etimes,rss,args | grep _r1_exp | grep -v grep | cut -c1-95
