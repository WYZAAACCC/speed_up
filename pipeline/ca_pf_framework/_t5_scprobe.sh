#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _supercrit_probe 的定义与判据行 ==="
grep -n 'def _supercrit_probe' windowB_surface.py
grep -n 'sc_last_fcrit\|sc_last_df\|sc_last_ed\|sc_try\|supercrit' windowB_surface.py | head -40 | cut -c1-175
