#!/bin/bash
# 一键查看所有任务的进度

echo "=============== 并行仿真 ==============="
for rid in 1 2 3 4; do
    f="/root/work/multi/run$rid/out.csv"
    if [ -f "$f" ]; then
        n=$(($(wc -l < "$f") - 1))
        last=$(tail -1 "$f")
        t=$(echo "$last" | cut -d, -f1)
        g=$(echo "$last" | cut -d, -f5)
        echo "  run$rid: $n 步, t=$t, 晶粒 $g"
    else
        echo "  run$rid: 无 CSV  (日志尾:)"
        tail -2 "/root/work/multi/run$rid/run.log" 2>/dev/null | sed 's/^/        /'
    fi
done

echo
echo "=============== 回放训练 ==============="
tail -4 /root/work/roll2.log 2>/dev/null || echo "  (无日志)"

echo
echo "=============== 资源 ==============="
uptime
free -g | head -2
echo -n "  GPU: "
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || echo "n/a"

echo
echo "=============== 进程内存 (MB) ==============="
tot=0
for p in $(pgrep -f 'phase_field-opt'); do
    r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
    tot=$((tot + ${r:-0}))
done
echo "  MOOSE 合计: $((tot / 1024)) MB"
