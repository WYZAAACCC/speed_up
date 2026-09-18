#!/bin/bash
echo "现在 $(date '+%H:%M:%S')"
echo
echo "############ 雅可比自检（缩网格 20x8）############"
for t in no2b D2b; do
  L=/root/work/s1d_jac/$t.log
  echo "--- $t ---"
  if [ ! -f "$L" ]; then echo "  未开始"; continue; fi
  grep -a "Finished Setting Up" "$L" | sed 's/^/  /'
  printf "  收敛步="; grep -ac "Solve Converged" "$L"
  grep -a "J - Jfd" "$L" | head -3 | sed 's/^/  /'
  grep -a -m1 -E '\*\*\* ERROR|NANORINF' "$L" | sed 's/^/  /'
done
echo
echo "############ W1（删掉纯输出的 grad_align）/ W3（2b 挪到 mu）############"
for t in W1 W3; do
  L=/root/work/s1d_w13/$t.log
  echo "--- $t ---"
  if [ ! -f "$L" ]; then echo "  未开始"; continue; fi
  grep -a "Finished Setting Up" "$L" | sed 's/^/  /'
  printf "  收敛步="; grep -ac "Solve Converged" "$L"
  echo "  残差序列:"; grep -a "Nonlinear |R|" "$L" | head -8 | sed 's/^/    /'
  grep -a -m1 -E '\*\*\* ERROR|NANORINF' "$L" | sed 's/^/  /'
done
echo
echo "############ 进程 ############"
pgrep -a phase_field-opt | head -4 || echo "  无 MOOSE 进程"
