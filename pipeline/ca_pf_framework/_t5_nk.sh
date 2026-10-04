#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== mm['n_%d'] / mm['vol_%d'] 是在哪里算出来的 ==="
grep -n "'n_%d'\|\"n_%d\"\|n_%d\|'vol_%d'" _bk_exp.py | cut -c1-175
echo
echo "=== 含 n_ 的 mm 装配处 ==="
grep -n "mm\['vol_\|mm\['n_\|_mm\[" _bk_exp.py | head -20 | cut -c1-175
