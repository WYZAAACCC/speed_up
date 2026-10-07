#!/bin/bash
# _r1_gatedbg.sh --- 诊断队列 v4（pid 4116）为何没在活跃数降到 2 时启动
P=${1:-4116}
echo "=== 队列进程 $P ==="
if [ ! -d "/proc/$P" ]; then echo "⛔ 进程已不在"; exit 0; fi
echo "state  = $(ps -o stat= -p "$P" | tr -d ' ')"
echo "wchan  = $(cat /proc/$P/wchan 2>/dev/null)"
echo "cmdline= $(tr '\0' ' ' < /proc/$P/cmdline)"
echo "子进程："
ps --ppid "$P" -o pid,stat,args --no-headers 2>/dev/null | head -6
echo
echo "=== 队列脚本正在执行到哪一行（从 fd 偏移看）==="
ls -l /proc/$P/fd 2>/dev/null | grep -i drive | head -3
echo
echo "=== 当前活跃 _r1_exp 数（与队列内部同一命令）==="
n=$(pgrep -c -f '_r1_exp\.py' 2>/dev/null); echo "pgrep -c => ${n:-空}"
echo
echo "=== 队列自己的 stdout（应写入 _w2_r1drive4.log）==="
tail -3 /mnt/f/speed_up/pipeline/ca_pf_framework/_w2_r1drive4.log
