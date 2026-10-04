#!/bin/bash
# Locate the rejection message and the burst law; print tight context.
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== [1] where is the rejection message emitted ==="
grep -n '无可用空场' _bk_exp.py windowB_surface.py | cut -c1-220
echo
echo "=== [2] alpha_km_n_lath + koistinen in windowB_km.py ==="
grep -n 'def alpha_km_n_lath' -A 30 windowB_km.py | cut -c1-160
echo
echo "=== [3] burst block in _bk_exp.py ==="
grep -n 'burst_km' _bk_exp.py | cut -c1-160
