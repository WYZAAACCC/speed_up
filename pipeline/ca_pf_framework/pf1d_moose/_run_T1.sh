#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
rm -f _R_*.log
run() { PROD1D_SUFFIX="$5" $P p1c_prod1d.py "$1" "$2" 1e-14 "$3" 0.6 1e-6 "$4" > "_R_A$1_W$2_$5.log" 2>&1 & }
run 0 2e-6    3.0e-4 300 L300
run 2 2e-6    3.0e-4 300 L300
run 4 2e-6    3.0e-4 300 L300
run 8 2e-6    1.5e-4 150 L150
run 2 2e-6    1.5e-4 150 L150
run 2 4e-6    1.5e-4 150 L150
run 2 1.05e-7 1.5e-4 150 L150
run 4 4e-6    1.5e-4 150 L150
run 4 1.05e-7 1.5e-4 150 L150
run 8 1.05e-7 1.5e-4 150 L150
wait
echo "===== ALL DONE ====="
grep -H 'rc=\|c_int=' _R_*.log