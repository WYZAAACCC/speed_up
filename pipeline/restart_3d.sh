#!/bin/bash
# 杀掉卡住的 3D 算例
# 原因：216,000 单元 × 21 变量把内存耗尽，十几分钟没完成一个时间步

echo "=== 杀掉现有 MOOSE 进程 ==="
pkill -f phase_field-opt 2>/dev/null
pkill -f "mpirun.*phase_field" 2>/dev/null
sleep 3
n=$(pgrep -c phase_field-opt 2>/dev/null || echo 0)
echo "  剩余进程: $n"

echo
echo "=== 内存释放情况 ==="
free -g | head -2

echo
echo "=== 清理旧输出 ==="
rm -f /root/work/phase1/phase1_3d*.e /root/work/phase1/phase1_3d_out.csv
ls /root/work/phase1/ 2>/dev/null
