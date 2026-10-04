#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== BM 是哪个模块 ==="
grep -n "^import\|^from" _bk_exp.py | grep -i "bm\|km" | cut -c1-140
echo
echo "=== measure_state 定义与 n_ 键的赋值 ==="
for F in windowB_km.py windowB_surface.py windowB_closure.py; do
  [ -f "$F" ] || continue
  echo "--- $F ---"
  grep -n "def measure_state\|'n_%d'\|\"n_%d\"\|n_%d\|thick" $F | head -14 | cut -c1-175
done
