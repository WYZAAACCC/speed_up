#!/usr/bin/env bash
# _run_t11j.sh --- A1+A2 之后的回归：T11j（界面速度 / Gibbs–Thomson 临界半径）。
#   这是 Window B 的**定义性判据**（Gibbs 面的表示精度不依赖分辨率），
#   A1 改了曲率路径 ⇒ 必须复跑。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
setsid nohup "$PY" -u T11j_verdict.py > _t11j_after_a1a2.log 2>&1 < /dev/null &
echo "T11j pid=$!"
sleep 15
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-70
free -g | head -2
