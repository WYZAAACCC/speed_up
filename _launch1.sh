cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose
PY=/root/miniconda3/envs/ml/bin/python
# T1.1a 长行程（180 µm, nx=300）
setsid nohup $PY -u p1c_prod1d.py 0 2e-6 1e-14 3.0e-4 0.6 1e-6 300 > _L_A0.log 2>&1 < /dev/null &
setsid nohup $PY -u p1c_prod1d.py 2 2e-6 1e-14 3.0e-4 0.6 1e-6 300 > _L_A2.log 2>&1 < /dev/null &
# T1.1b 大 ALPHA（90 µm, nx=150）
setsid nohup $PY -u p1c_prod1d.py 4 2e-6 1e-14 1.5e-4 0.6 1e-6 150 > _L_A4.log 2>&1 < /dev/null &
setsid nohup $PY -u p1c_prod1d.py 8 2e-6 1e-14 1.5e-4 0.6 1e-6 150 > _L_A8.log 2>&1 < /dev/null &
sleep 8
echo "已启动 MOOSE 作业数: $(ps -eo args | grep -c '[p]hase_field-opt')"