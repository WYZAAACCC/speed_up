#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
export PROD1D_DT=4.1667e-8      # fixed dt = 0.05 dx^2/D_L  (adaptive dt reverted)
rm -f _D_*.log
run() { # ALPHA WF tend nx suffix [DT]
  local dt="${6:-4.1667e-8}"
  PROD1D_SUFFIX="$5" PROD1D_DT="$dt" $P p1c_prod1d.py "$1" "$2" 1e-14 "$3" 0.6 1e-6 "$4" \
      > "_D_$5_A$1_W$2.log" 2>&1 &
}
run 0 2e-6    1.5e-4 150 L150
run 2 2e-6    1.5e-4 150 L150
run 4 2e-6    1.5e-4 150 L150
run 2 2e-6    3.0e-4 300 L300
run 2 2e-6    1.5e-4 150 L150dt4 1.0417e-8
run 2 4e-6    1.5e-4 150 L150
run 2 1.05e-7 1.5e-4 150 L150
run 4 1.05e-7 1.5e-4 150 L150
wait
echo "===== DONE ====="
grep -H 'rc=\|dt =\|c_int=' _D_*.log