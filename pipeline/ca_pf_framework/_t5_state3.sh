#!/bin/bash
# Verify eta patch content + launcher argv + burst law code.
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

echo "=== [A] eta patch: the 2 ed_eta lines in live file ==="
grep -n 'ed_eta' windowB_surface.py
echo
echo "--- diff live vs .bak_stacksc (no-patch) ---"
diff <(cat windowB_surface.py.bak_stacksc) <(cat windowB_surface.py) | head -30
echo
echo "=== [B] _t5_final.sh ==="
cat _t5_final.sh
echo
echo "=== [C] _t5_ablate.sh ==="
cat _t5_ablate.sh
echo
echo "=== [D] t5FIX log header (argv as printed by engine) ==="
grep -a -m1 -A3 'sys.argv\|ARGV\|argv=' _w2_t5_short_t5FIX.log 2>/dev/null | cut -c1-400
echo "--- first 6 lines of t5FIX log ---"
head -6 _w2_t5_short_t5FIX.log | cut -c1-200
