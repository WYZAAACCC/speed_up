#!/bin/bash
# 深查：全尺寸与 MPI n=1 是否真的卡住（还是日志未 flush）。
echo "############ 全尺寸 bench.i ############"
L=/root/work/bench_full/run.log
echo "  文件大小 $(stat -c%s $L) 字节，最后修改 $(stat -c%y $L | cut -d. -f1)"
echo "  当前时间 $(date '+%Y-%m-%d %H:%M:%S')"
echo "  --- 末尾 20 行 ---"
sed 's/\x1b\[[0-9;]*m//g' "$L" | tail -20 | sed 's/^/    /'
echo "  --- 时间步与牛顿计数 ---"
echo "    Time Step 行数: $(grep -ac '^Time Step' $L)"
echo "    Nonlinear 行数: $(grep -ac 'Nonlinear |R|' $L)"
echo "    Jacobian 次数: $(grep -ac 'Computing Jacobian' $L)"

echo
echo "############ MPI n=1 ############"
L2=/root/work/mpi_scale/n1/run.log
echo "  文件大小 $(stat -c%s $L2) 字节，最后修改 $(stat -c%y $L2 | cut -d. -f1)"
echo "  --- 末尾 12 行 ---"
sed 's/\x1b\[[0-9;]*m//g' "$L2" | tail -12 | sed 's/^/    /'
echo "  --- 时间步 ---"
grep -a '^Time Step' "$L2" | tail -4 | sed 's/^/    /'

echo
echo "############ 性能扫描 P0 ############"
L3=/root/work/perf_opt/P0/run.log
echo "  文件大小 $(stat -c%s $L3) 字节"
sed 's/\x1b\[[0-9;]*m//g' "$L3" | tail -8 | sed 's/^/    /'
