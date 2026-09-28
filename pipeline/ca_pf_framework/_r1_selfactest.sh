#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
# 后台跑，避免被调用方的超时打断
setsid nohup $PY -u _r1_selfac.py --snap _exp/e7_selfac/snap_00050.npz \
    --nrand 12 --workers 4 > _w2_r1selfac_test.log 2>&1 < /dev/null &
echo "started pid=$!"
sleep 10
ps -eo pid,etimes,rss,args | grep _r1_selfac | grep -v grep | cut -c1-100
free -g | head -2
