#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _bk_measure.py 里的 n_%d / vol_%d ==="
grep -n "n_%d\|vol_%d\|def measure_state" _bk_measure.py | head -20 | cut -c1-180
echo
echo "=== n_k 的赋值上下文 ==="
L=$(grep -n "n_%d" _bk_measure.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then S=$((L-14)); E=$((L+3)); sed -n "${S},${E}p" _bk_measure.py | cut -c1-165; fi
