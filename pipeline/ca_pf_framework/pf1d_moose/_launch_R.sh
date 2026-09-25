#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
# remove the polluted instrument directories (disposable outputs, not source)
rm -rf prod1d_A0_W2_kc1e-14 prod1d_A2_W2_kc1e-14 prod1d_A4_W2_kc1e-14 prod1d_A8_W2_kc1e-14
rm -f _T12_*.log
run() { # ALPHA  WF  tend  nx  suffix
  PROD1D_SUFFIX="$5" nohup $P p1c_prod1d.py "$1" "$2" 1e-14 "$3" 0.6 1e-6 "$4" \
      > "_R_A$1_W$2_$5.log" 2>&1 &
  echo "started A=$1 WF=$2 tend=$3 nx=$4 [$5] pid=$!"
}
# --- T1.1a travel convergence (180 um) ---
run 0 2e-6    3.0e-4 300 L300
run 2 2e-6    3.0e-4 300 L300
run 4 2e-6    3.0e-4 300 L300
# --- T1.1b large ALPHA (90 um) ---
run 8 2e-6    1.5e-4 150 L150
# --- T1.2  W_F three-way at ALPHA=2 (production value) + W_F=w_c at A4/A8 ---
run 2 2e-6    1.5e-4 150 L150
run 2 4e-6    1.5e-4 150 L150
run 2 1.05e-7 1.5e-4 150 L150
run 4 4e-6    1.5e-4 150 L150
run 4 1.05e-7 1.5e-4 150 L150
run 8 1.05e-7 1.5e-4 150 L150
sleep 6
ps -eo pid,args | grep 'p1c_prod1d.py' | grep -v grep | wc -l