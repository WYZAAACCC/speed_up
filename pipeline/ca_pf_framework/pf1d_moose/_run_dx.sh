#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
run() { PROD1D_SUFFIX="$5" PROD1D_DT=4.1667e-8 $P p1c_prod1d.py "$1" "$2" 1e-14 "$3" 0.6 "$6" "$4" > "_X_$5_A$1.log" 2>&1 & }
run 2    2e-6 1.5e-4 200 dx050 5.0e-7
run 2.58 2e-6 1.5e-4 200 dx050 5.0e-7
run 2    2e-6 1.5e-4 400 dx025 2.5e-7
wait
echo "===== DX DONE ====="
grep -H 'rc=\|c_int=' _X_*.log