cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
T21B_TEND=600 $PY _t21b8_run2.py 0.002 3e-7 1.2e-6 S600 32 > _t21b8_S600.log 2>&1 &
T21B_TEND=500 $PY _t21b8_run2.py 0.002 3e-7 1.2e-6 S500 32 > _t21b8_S500.log 2>&1 &
T21B_TEND=400 $PY _t21b8_run2.py 0.002 3e-7 1.2e-6 S400 32 > _t21b8_S400.log 2>&1 &
T21B_TEND=350 $PY _t21b8_run2.py 0.002 3e-7 1.2e-6 S350 32 > _t21b8_S350.log 2>&1 &
wait
echo S_DONE
