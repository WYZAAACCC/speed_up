#!/usr/bin/env bash
# _run_t21.sh --- B3：β 标定扫描（2D 截面口径，与文献同一个量）。setsid 脱离。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,2.0,3.5,5.0,6.5 --f-target 0.05 > _t21.log 2>&1 < /dev/null &
echo "T21 pid=$!"
sleep 15
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-72
free -g | head -2
