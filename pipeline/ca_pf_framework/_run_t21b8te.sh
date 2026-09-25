cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
T21B_TEND=550 $PY _t21b8_run2.py 0.011 3e-7 1.2e-6 TE550 32 > _t21b8_TE550.log 2>&1 &
T21B_TEND=450 $PY _t21b8_run2.py 0.011 3e-7 1.2e-6 TE450 32 > _t21b8_TE450.log 2>&1 &
T21B_TEND=350 $PY _t21b8_run2.py 0.011 3e-7 1.2e-6 TE350 32 > _t21b8_TE350.log 2>&1 &
wait
echo TE_DONE
