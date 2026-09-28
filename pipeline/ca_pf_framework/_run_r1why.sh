#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
setsid nohup $PY -u _r1_normwhy.py --steps 120 --th 2 > _w2_r1normwhy.log 2>&1 < /dev/null &
echo "started normwhy pid=$!"
sleep 8
ps -eo pid,etimes,rss,args | grep -E "_r1_" | grep -v grep | cut -c1-120
free -g | head -2
