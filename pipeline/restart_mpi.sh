#!/bin/bash
# 停掉被 SIGHUP 打断的旧 MPI 测试，用修好 setsid 的版本重启。
# 【教训】后台脚本里的子进程必须用 setsid --wait 包住，否则启动它的
#         外层 wsl 命令一退出，子进程就吃 SIGHUP（rc=129）。
for P in $(pgrep -f 'mpi.i'); do kill -9 "$P" 2>/dev/null; done
for P in $(pgrep -f 'ms.sh'); do kill -9 "$P" 2>/dev/null; done
sleep 2
echo "旧进程已清，剩余 $(ps -eo comm | grep -c phase_field)"
sed 's/\r$//' /mnt/f/speed_up/pipeline/mpi_scale.sh > /root/work/ms.sh
nohup bash /root/work/ms.sh > /root/work/ms.log 2>&1 &
sleep 5
echo "已重启 MPI 扩展性测试"
