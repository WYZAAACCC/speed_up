cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
$PY _t21b8_run.py 0.005 5e-7 0 a0.005 32 > _t21b8_0.005.log 2>&1 &
$PY _t21b8_run.py 0.011 5e-7 0 a0.011 32 > _t21b8_0.011.log 2>&1 &
$PY _t21b8_run.py 0.020 5e-7 0 a0.020 32 > _t21b8_0.020.log 2>&1 &
$PY _t21b8_run.py 0.011 3e-7 2e-7 hold 32 > _t21b8_hold.log 2>&1 &
wait
echo T21B8_DONE
