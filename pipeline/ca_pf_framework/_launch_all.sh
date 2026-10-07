#!/usr/bin/env bash
# _launch_all.sh --- 用 setsid 分离启动本轮所有长作业（会话中断也不会带走它们）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.10 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16prod  pid=$!"
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128,256 \
        --f-target 0.10 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b     pid=$!"
setsid nohup "$PY" -u T8_verify_Mcalib.py > _t8.log 2>&1 < /dev/null &
echo "T8       pid=$!"
sleep 25
echo '--- alive ---'
ps -o pid,sess,etime,pcpu,rss,args --no-headers -C python | cut -c1-118
