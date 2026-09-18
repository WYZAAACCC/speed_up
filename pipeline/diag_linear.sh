#!/bin/bash
# 看线性求解是否失败/触顶 —— 若线性解不到位，牛顿残差会出现非零地板
DL=/root/work/s1d_smoke/run.log
CL=/root/work/s1c_col/run.log

echo "=== D 版：线性求解状态 ==="
grep -a "Linear solve" "$DL" | head -14

echo
echo "=== C 版：线性求解状态 ==="
grep -a "Linear solve" "$CL" | head -10

echo
echo "=== D 版：线性迭代数分布 ==="
grep -a -oE "iterations [0-9]+" "$DL" | sort | uniq -c | sort -rn | head

echo
echo "=== C 版：线性迭代数分布 ==="
grep -a -oE "iterations [0-9]+" "$CL" | sort | uniq -c | sort -rn | head

echo
echo "=== 两版求解器设置 ==="
for f in /root/work/s1d_smoke/in.i /root/work/s1c_col/in.i; do
  echo "--- $f ---"
  grep -a -E "l_max_its|l_tol|nl_max_its|nl_rel_tol|nl_abs_tol" "$f"
done
