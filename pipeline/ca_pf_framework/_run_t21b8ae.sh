cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
T21B_TEND=350 T21B_FT=KM T21B_AE=1 $PY _t21b8_run4.py 0.005 3e-7 8e-7 AE0.005_350 32 > _t21b8_AE.log 2>&1 &
wait
echo AE_DONE
