#!/bin/bash
# 停掉一切：生产跑、加速基准、以及它们的自报循环。
# 用户指示：优先用最快速度证明正确性与收敛性，生产先不启动。
pgrep -f 'phase_field-opt' > /tmp/p1.txt 2>/dev/null
xargs -r kill -9 < /tmp/p1.txt 2>/dev/null
pgrep -f 'mpiexec' > /tmp/p2.txt 2>/dev/null
xargs -r kill -9 < /tmp/p2.txt 2>/dev/null
pgrep -f 'run_nonad_prod|bench_speed|run_conv_demo' > /tmp/p3.txt 2>/dev/null
xargs -r kill -9 < /tmp/p3.txt 2>/dev/null
sleep 4
echo "剩余 MOOSE: $(ps -eo comm | grep -c phase_field)"
echo "剩余 mpiexec: $(ps -eo comm | grep -c mpiexec)"
echo "负载: $(uptime | sed 's/.*load average/load/')"
echo "可用内存: $(free -g | awk 'NR==2{print $7}') GB"
