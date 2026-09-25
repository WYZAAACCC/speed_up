cd /mnt/f/speed_up/pipeline/ca_pf_framework
export OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
python3 -c "import os; os.path.exists('_t21b_scan3.csv') and os.remove('_t21b_scan3.csv')"
sed 's/_t21b_scan2.csv/_t21b_scan3.csv/' _t21b_scan2.py > _t21b_scan3.py
$PY _t21b_scan3.py 0.3 4e-6 32 > _t21b3_a0.3.log 2>&1 &
$PY _t21b_scan3.py 0.5 4e-6 32 > _t21b3_a0.5.log 2>&1 &
$PY _t21b_scan3.py 0.8 4e-6 32 > _t21b3_a0.8.log 2>&1 &
$PY _t21b_scan3.py 1.2 4e-6 32 > _t21b3_a1.2.log 2>&1 &
$PY _t21b_scan3.py 2.0 4e-6 32 > _t21b3_a2.0.log 2>&1 &
$PY _t21b_scan3.py 0.8 8e-6 32 > _t21b3_plat.log 2>&1 &
wait
cat _t21b_scan3.csv
echo SCAN3_DONE
