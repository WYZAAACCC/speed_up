#!/bin/bash
# 关键疑点：M2（MUMPS, nl_abs_tol=1e-9）15 步全收敛；A（同样是 MUMPS, nl_abs_tol=1e-9）
# 只走 3 步就失败。两者都源自 C_nonad.i。**必须找出差异**，否则 A2 结论不成立。
#
# 顺带看 A 失败处的牛顿轨迹，判断是"卡住"还是"震荡"。
echo "############ 1. A.i vs M2.i 的差异 ############"
diff <(grep -vE '^\s*#' /root/work/slv_cmp/A/A.i) <(grep -vE '^\s*#' /root/work/s1d_mumps/M2/M2.i) \
  | head -40
echo "(无输出 = 除注释外完全相同)"

echo
echo "############ 2. A.i vs B.i 的差异（应只有求解器与 nl_abs_tol）############"
diff <(grep -vE '^\s*#' /root/work/slv_cmp/A/A.i) <(grep -vE '^\s*#' /root/work/slv_cmp/B/B.i) | head -20

echo
echo "############ 3. A 失败的完整牛顿轨迹（末尾 30 行）############"
sed 's/\x1b\[[0-9;]*m//g' /root/work/slv_cmp/A/run.log | grep -aE 'Time Step|Nonlinear \|R\||DIVERGED|did not converge|dt =' | tail -45

echo
echo "############ 4. 两者 TimeStepper 设置 ############"
sed -n '/\[TimeStepper\]/,/^\[\]/p' /root/work/slv_cmp/A/A.i
