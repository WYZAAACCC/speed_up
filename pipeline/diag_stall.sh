#!/bin/bash
# 定位残差停滞发生在哪个方程：看 Outlier Variable Residual Norms
# 并对比 C 版（已验证收敛）第 1 步的同一指标
DL=/root/work/s1d_smoke/run.log
CL=/root/work/s1c_col/run.log

echo "=== D 版（停滞）第 1 步的离群变量残差 ==="
grep -a -A8 "Outlier Variable Residual Norms" "$DL" | head -20

echo
echo "=== C 版（正常）第 1 步的离群变量残差 ==="
grep -a -A8 "Outlier Variable Residual Norms" "$CL" | head -20

echo
echo "=== 两版第 1 步的残差序列对比 ==="
echo "--- D 版 ---"
grep -a "Nonlinear |R|" "$DL" | head -12
echo "--- C 版 ---"
grep -a "Nonlinear |R|" "$CL" | head -12

echo
echo "=== 两版收敛容差设置 ==="
grep -a -E "nl_rel_tol|nl_abs_tol" /root/work/s1d_smoke/in.i

echo
echo "=== D 版第 1 步各阶段耗时 ==="
grep -a -E "Computing Jacobian|Linear solve|Finished Solving" "$DL" | head -10
