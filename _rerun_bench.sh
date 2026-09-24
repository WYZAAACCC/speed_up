#!/bin/bash
for p in $(ps -eo pid,args | grep '[w]indowB_bench' | awk '{print $1}'); do kill -9 $p 2>/dev/null; done
sleep 1
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _fix_bench.py
cd pipeline/ca_pf_framework
OMP_NUM_THREADS=1 nohup /root/miniconda3/envs/ml/bin/python -u windowB_bench.py > /tmp/wb4.log 2>&1 < /dev/null &
sleep 50; cat /tmp/wb4.log