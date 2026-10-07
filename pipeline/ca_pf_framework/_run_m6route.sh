#!/bin/bash
# P0.3 并行扫描：5 档，每档 4 线程（5x4=20 = 本机逻辑核数）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
run() { OMP_NUM_THREADS=4 timeout 5400  _chk_m6_route.py "" > _m6route_.log 2>&1; echo "done  rc=0"; }
run --tag A --aniso 0.0  --pair 0 --nstep 120 &
run --tag B --aniso 0.4  --pair 0 --nstep 120 &
run --tag C --aniso 0.4  --pair 1 --nstep 120 &
run --tag D --aniso 0.9  --pair 1 --nstep 120 &
run --tag E --aniso 0.4  --pair 1 --nstep 120 --df 2e7 &
wait
echo ALL_DONE
