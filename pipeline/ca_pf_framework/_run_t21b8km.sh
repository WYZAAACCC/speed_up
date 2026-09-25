cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
T21B_TEND=350 T21B_FT=KM $PY _t21b8_run3.py 0.005 3e-7 8e-7 KM0.005_350 32 > _t21b8_KM0.005_350.log 2>&1 &
T21B_TEND=500 T21B_FT=KM $PY _t21b8_run3.py 0.005 3e-7 8e-7 KM0.005_500 32 > _t21b8_KM0.005_500.log 2>&1 &
T21B_TEND=350 T21B_FT=KM $PY _t21b8_run3.py 0.011 3e-7 8e-7 KM0.011_350 32 > _t21b8_KM0.011_350.log 2>&1 &
T21B_TEND=500 T21B_FT=KM $PY _t21b8_run3.py 0.011 3e-7 8e-7 KM0.011_500 32 > _t21b8_KM0.011_500.log 2>&1 &
T21B_TEND=350 T21B_FT=KM $PY _t21b8_run3.py 0.020 3e-7 8e-7 KM0.020_350 32 > _t21b8_KM0.020_350.log 2>&1 &
T21B_TEND=500 T21B_FT=KM $PY _t21b8_run3.py 0.020 3e-7 8e-7 KM0.020_500 32 > _t21b8_KM0.020_500.log 2>&1 &
wait
echo KM_DONE
