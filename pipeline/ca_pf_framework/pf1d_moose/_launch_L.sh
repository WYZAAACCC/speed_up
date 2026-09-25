#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PATH=/root/miniconda3/envs/moose/bin:$PATH
P=/root/miniconda3/envs/ml/bin/python
run() {
  nohup $P p1c_prod1d.py "$@" > "_L_A$1.log" 2>&1 &
  echo "started $* pid=$!"
}
run 0 2e-6 1e-14 3.0e-4 0.6 1e-6 300
run 2 2e-6 1e-14 3.0e-4 0.6 1e-6 300
run 4 2e-6 1e-14 1.5e-4 0.6 1e-6 150
run 8 2e-6 1e-14 1.5e-4 0.6 1e-6 150
sleep 5
ps -eo pid,args | grep '_p1c_prod1d\|p1c_prod1d.py' | grep -v grep