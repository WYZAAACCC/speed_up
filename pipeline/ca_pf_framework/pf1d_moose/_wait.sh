cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose
for i in $(seq 1 10); do
  n=$(ps -eo args | grep -c '[p]hase_field-opt')
  echo "等待中: 还有 $n 个 MOOSE 进程"
  if [ "$n" -eq 0 ]; then break; fi
  sleep 120
done
/root/miniconda3/envs/ml/bin/python -u collect_thin.py ak3_p1c_kcw