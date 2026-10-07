#!/usr/bin/env bash
# _restart_t13b2.sh --- T13b 用**固定 f 插值采样**重启（旧的"第一个跨过目标的样本"口径
#   会让三档落点各不相同 ⇒ 判据实际上在比"不同 f 上的统计量"，对定标律是系统性偏置）。
#   T24rve 不重启：它只报**单个**态的分布（不是跨档比较），落点不同只是记账问题。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128,256 \
        --f-target 0.10 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-72
