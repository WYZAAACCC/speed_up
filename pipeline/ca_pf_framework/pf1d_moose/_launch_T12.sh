#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
# T1.2 -- W_F three-way comparison on the production formula (dx=1um, 90um travel)
run() { nohup $P p1c_prod1d.py "$@" > "_T12_$1_W$2.log" 2>&1 & echo "started $* pid=$!"; }
run 2 2e-6 1e-14 1.5e-4 0.6 1e-6 150      # production frozen W_F
run 2 4e-6 1e-14 1.5e-4 0.6 1e-6 150      # = int_width
run 2 1.05e-7 1e-14 1.5e-4 0.6 1e-6 150   # = w_c (c-profile width)
run 4 1.05e-7 1e-14 1.5e-4 0.6 1e-6 150   # ALPHA=4 with w_c
run 8 1.05e-7 1e-14 1.5e-4 0.6 1e-6 150   # ALPHA=8 with w_c
run 8 2e-6 1e-14 1.5e-4 0.6 1e-6 150 200  # ALPHA=8, more Newton its (extra arg ignored -> see script)
sleep 5
ps -eo pid,args | grep 'p1c_prod1d.py' | grep -v grep | wc -l