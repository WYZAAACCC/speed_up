#!/bin/bash
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
echo "=== k1ng(NO_GIBBS) ? f_loc / M ==="
grep -n -A4 "property_name = f_loc" stage1_meltpool_nogb3d_k1ng.i | head -20
echo "=== k1ng ? solute_mobility ==="
grep -n -A4 "property_name = M" stage1_meltpool_nogb3d_k1ng.i | head -20
echo "=== ch_kappa ? ==="
sed -n '915,935p' stage1_meltpool_gibbs3d_k4base.i
echo "=== ????? f_loc / ch_kappa ==="
grep -n -A6 "property_name = f_loc" /mnt/f/speed_up/pipeline/stage1_meltpool_c.i | head -30
echo "--- ?? ch_kappa ---"
grep -n -A6 "\[ch_kappa\]" /mnt/f/speed_up/pipeline/stage1_meltpool_c.i
