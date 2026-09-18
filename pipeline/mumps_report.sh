#!/bin/bash
# 汇总 MUMPS 测试（M1=AD+MUMPS, M2=非AD+MUMPS）的收敛情况。
for T in M1 M2; do
  L=/root/work/s1d_mumps/$T/run.log
  echo "=============================================="
  echo "  $T"
  echo "=============================================="
  if [ ! -f "$L" ]; then echo "  无日志"; continue; fi
  NS=$(grep -ac 'Solve Converged' "$L")
  ND=$(grep -ac 'DIVERGED' "$L")
  echo "  收敛时间步数 = $NS   线性失败次数 = $ND"
  echo "  --- 牛顿末 12 次 ---"
  grep -a 'Nonlinear |R|' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -12 | sed 's/^/    /'
  echo "  --- 末 5 个时间步 ---"
  grep -a '^Time Step' "$L" | tail -5 | sed 's/^/    /'
  echo "  --- 报错 ---"
  grep -a -m3 -E '\*\*\* ERROR|Aborting|out of memory' "$L" | sed 's/^/    /'
  echo "  --- 耗时 ---"
  grep -a -oE 'Finished Executing[^]]*\] \[[^]]*\]' "$L" | tail -1 | sed 's/^/    /'
done
echo
echo "=== 正在运行 ==="
ps -eo pid,etime,comm | grep phase_field | grep -v grep
