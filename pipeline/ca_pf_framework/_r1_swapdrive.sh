#!/bin/bash
# 换掉正在等的老驱动（v2），改用按 E_min 重排优先级的 v3
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
bash -n _r1_drive3.sh && echo BASH_OK || exit 1
# 只杀"在等"的驱动 shell，不动仿真进程
for P in $(pgrep -f "_r1_drive2.sh" 2>/dev/null); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *"_r1_exp.py"*) ;; *) echo "kill driver $P : $C"; kill -9 "$P" 2>/dev/null;; esac
done
sleep 2
# 检查 v3 的 e7d 目标目录是否存在
mkdir -p _exp/e7d_pair34
setsid nohup bash _r1_drive3.sh > /dev/null 2>&1 < /dev/null &
echo "v3 driver started"
sleep 6
ps -eo pid,etimes,args | grep -E '_r1_exp|_r1_drive|_r1_waitdx' | grep -v grep | cut -c1-72
free -g | head -2
