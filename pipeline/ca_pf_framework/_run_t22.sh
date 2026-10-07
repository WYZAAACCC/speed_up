#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
setsid nohup "$PY" -u T22_verify_paircurv.py --N 64 --dx-nm 25 > _t22.log 2>&1 < /dev/null &
echo "T22 pid=$!"
sleep 12
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-80
