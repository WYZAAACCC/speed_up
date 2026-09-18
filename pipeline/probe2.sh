#!/bin/bash
echo "===== 3D 试探算例结果 ====="
cat /root/work/phase1/phase1_3d_out.csv

echo
echo "===== multi2 最新 ====="
for r in 1 2; do
    f=/root/work/multi2/run$r/in_out.csv
    n=$(( $(wc -l < "$f") - 1 ))
    echo "  run$r: $n 个输出点 | $(tail -1 "$f")"
done

echo
echo "===== multi2 启动时刻 ====="
ps -eo pid,etime,args | grep -E 'mpirun -np 8' | grep -v grep
