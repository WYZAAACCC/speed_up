cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
python3 -c "import os; os.path.exists('_t21b_scan2.csv') and os.remove('_t21b_scan2.csv')"
$PY _t21b_scan2.py 0.5 4e-7 32 > _t21b2_a0.5.log 2>&1 &
$PY _t21b_scan2.py 1.0 4e-7 32 > _t21b2_a1.0.log 2>&1 &
$PY _t21b_scan2.py 2.0 4e-7 32 > _t21b2_a2.0.log 2>&1 &
$PY _t21b_scan2.py 3.0 4e-7 32 > _t21b2_a3.0.log 2>&1 &
$PY _t21b_scan2.py 5.0 4e-7 32 > _t21b2_a5.0.log 2>&1 &
$PY _t21b_scan2.py 2.0 8e-7 32 > _t21b2_plat.log 2>&1 &
wait
echo "=== scan2 ==="
cat _t21b_scan2.csv
echo SCAN2_DONE
