cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
$PY _t21b_traj.py 0.50 300 32 > _t21b_traj_0.50.log 2>&1 &
$PY _t21b_traj.py 1.00 300 32 > _t21b_traj_1.00.log 2>&1 &
$PY _t21b_traj.py 2.00 300 32 > _t21b_traj_2.00.log 2>&1 &
$PY _t21b_traj.py 4.00 300 32 > _t21b_traj_4.00.log 2>&1 &
wait
echo TRAJ_DONE
