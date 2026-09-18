#!/bin/bash
# 观察 D 版 smoke test 的推进情况与收敛行为
L=/root/work/s1d_smoke/run.log
echo "现在: $(date '+%H:%M:%S')"
echo
echo "=== 推进情况 ==="
printf "  已完成步数: "; grep -ac "Solve Converged" "$L"
printf "  已开始的 Time Step: "; grep -ac "^Time Step" "$L"
grep -a "^Time Step" "$L" | tail -4
echo
echo "=== 当前步的非线性迭代残差（最近 12 行）==="
grep -a "Nonlinear |R|" "$L" | tail -12
echo
echo "=== 各阶段耗时（最近的几项）==="
grep -a -E "Computing Jacobian|Linear solve|Solve Converged|Finished Setting Up" "$L" | tail -8
echo
echo "=== 内存 ==="
PID=$(pgrep -f phase_field-opt | head -1)
if [ -n "$PID" ]; then
  RSS=$(ps -o rss= -p "$PID")
  echo "  PID $PID  $(( RSS / 1024 )) MB"
else
  echo "  MOOSE 未在运行"
fi
echo
echo "=== 有无报错/发散关键字 ==="
grep -a -E "DIVERGED|NANORINF|ERROR|Did NOT Converge|dt = .*e-0[0-9]" "$L" | tail -5 || echo "  无"
