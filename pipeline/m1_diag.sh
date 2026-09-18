#!/bin/bash
# 诊断 M1（AD + MUMPS）为何不收敛：看 DIVERGED 类型、线性迭代数、时间步削减路径。
L=/root/work/s1d_mumps/M1/run.log
echo "############ M1 (AD + MUMPS) 诊断 ############"
echo "--- DIVERGED 类型分布 ---"
grep -a -oE 'DIVERGED_[A-Z_]+' "$L" | sort | uniq -c | sort -rn | sed 's/^/  /'
echo
echo "--- 线性求解迭代数分布（前 20 行）---"
grep -a 'Linear solve' "$L" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//' | sort | uniq -c | sort -rn | head -8 | sed 's/^/  /'
echo
echo "--- 时间步削减全过程 ---"
grep -a '^Time Step' "$L" | sed 's/^/  /'
echo
echo "--- 每次失败的上下文（DIVERGED 前 3 行）---"
grep -a -B3 'DIVERGED' "$L" | sed 's/\x1b\[[0-9;]*m//g' | head -24 | sed 's/^/  /'
echo
echo "############ 对照 M2 的线性求解 ############"
grep -a 'Linear solve' /root/work/s1d_mumps/M2/run.log | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//' | sort | uniq -c | sort -rn | head -6 | sed 's/^/  /'
echo
echo "--- M2 最后一次线性失败上下文 ---"
grep -a -B2 -A2 'DIVERGED' /root/work/s1d_mumps/M2/run.log | sed 's/\x1b\[[0-9;]*m//g' | head -12 | sed 's/^/  /'
