#!/bin/bash
# 汇报 sweep_fixed.sh 的结果。写成文件跑（Git Bash 会吞内联命令里的循环变量）。
echo "现在 $(date '+%H:%M:%S')  MOOSE 进程数=$(pgrep -cf 'phase_field-opt -i')"
echo
for t in S1_asm_base S2_asm_300 S3_asm_shift S4_hypre S5_asm_lvl2; do
  L="/root/work/s1d_sweep/$t/run.log"
  echo "--- $t ---"
  if [ ! -f "$L" ]; then echo "   未开始"; continue; fi
  printf "   收敛步=%s   末次牛顿残差=" "$(grep -ac 'Solve Converged' "$L")"
  grep -a "Nonlinear |R|" "$L" | tail -1 | sed 's/.*|R| = //' | sed 's/\x1b\[[0-9;]*m//g'
  echo "   牛顿轨迹:"
  grep -a "Nonlinear |R|" "$L" | head -7 | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^/     /'
  echo "   线性求解:"
  grep -a "Linear solve" "$L" | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' \
    | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
  grep -a -m2 -E '\*\*\* ERROR|SUBPC|zero pivot' "$L" | sed 's/^/     /'
done
