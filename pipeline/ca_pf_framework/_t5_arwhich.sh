#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 宽比/长厚 量具用的是哪个量？ ==="
for F in _t5_aralign.py _t5_aspect.py _t5_lathlen.py _t5_seven.py _t5_meterchk.py; do
  [ -f "$F" ] || continue
  echo "--- $F ---"
  grep -n "n_lath\|ths\|w_lath\|a_lath\|band_val\|region\|span" $F | head -10 | cut -c1-160
done
