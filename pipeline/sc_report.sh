#!/bin/bash
# 汇总 solver_compare 的 A(MUMPS, nl_abs_tol=1e-9) vs B(ASM, nl_abs_tol=1e-6)。
for T in A B; do
  L=/root/work/slv_cmp/$T/run.log
  echo "=============================================="
  echo "  $T   ($([ $T = A ] && echo 'MUMPS 精确 LU, nl_abs_tol=1e-9' || echo 'ASM+ILU, nl_abs_tol=1e-6'))"
  echo "=============================================="
  [ -f "$L" ] || { echo "  无日志"; continue; }
  echo "  收敛步数 = $(grep -ac 'Solve Converged' "$L")"
  echo "  线性失败 = $(grep -ac 'DIVERGED' "$L")"
  echo "  牛顿失败 = $(grep -ac 'did not converge' "$L")"
  echo "  末步时间 = $(grep -a '^Time Step' "$L" | tail -1)"
  echo "  --- 每个时间步的牛顿迭代数 ---"
  awk '/^Time Step/{ts=$0} /Nonlinear \|R\|/{n++} /Solve Converged/{printf "    %s -> %d 次牛顿\n", ts, n; n=0}' "$L" | tail -20
  echo "  --- 总耗时 ---"
  grep -a -oE '(Finished Solving|Finished Executing)[^]]*\] \[[^]]*\]' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -1 | sed 's/^/    /'
  echo "  --- 报错 ---"
  grep -a -m3 -E '\*\*\* ERROR|Aborting' "$L" | sed 's/^/    /'
done
echo
echo "=========== Exodus 输出（用于逐场对比）==========="
ls -la /root/work/slv_cmp/A/A.e /root/work/slv_cmp/B/B.e 2>/dev/null
