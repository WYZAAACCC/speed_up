#!/bin/bash
# 汇总 4 个对照变体的结果：收敛性、非线性迭代数、线性迭代数
D=/root/work/s1d_var
echo "现在 $(date '+%H:%M:%S')"
echo
printf '%-4s %-8s %-8s %-9s %-9s %s\n' 变体 setup 收敛步 非线性迭代 线性迭代 末步残差
echo "----------------------------------------------------------------------"
for v in v0 v1 v2 v3 v4; do
  L="$D/$v/run.log"
  if [ ! -f "$L" ]; then printf '%-4s 未开始\n' "$v"; continue; fi
  setup=$(grep -ac 'Finished Setting Up' "$L")
  nconv=$(grep -ac 'Solve Converged' "$L")
  nnit=$(grep -ac 'Nonlinear |R|' "$L")
  nlit=$(grep -ac 'Linear solve' "$L")
  lastR=$(grep -a 'Nonlinear |R|' "$L" | tail -1 | sed 's/.*= //')
  printf '%-4s %-8s %-8s %-9s %-9s %s\n' "$v" "$setup" "$nconv" "$nnit" "$nlit" "$lastR"
done

echo
echo "=== 各变体的非线性残差序列（前 12 个）==="
for v in v0 v1 v2 v3 v4; do
  L="$D/$v/run.log"
  [ -f "$L" ] || continue
  echo "--- $v ---"
  grep -a 'Nonlinear |R|' "$L" | head -12 | sed 's/^/  /'
done

echo
echo "=== 线性求解收敛情况（关键：是否触顶/未达容差）==="
for v in v0 v1 v2 v3 v4; do
  L="$D/$v/run.log"
  [ -f "$L" ] || continue
  echo "--- $v ---"
  grep -a 'Linear solve' "$L" | head -8 | sed 's/^/  /'
done

echo
echo "=== 有没有报错 ==="
for v in v0 v1 v2 v3 v4; do
  L="$D/$v/run.log"
  [ -f "$L" ] || continue
  err=$(grep -a -m2 -E '\*\*\* ERROR|NANORINF|DIVERGED|Did NOT Converge' "$L")
  [ -n "$err" ] && { echo "--- $v ---"; echo "$err" | sed 's/^/  /'; }
done
echo "（无输出=四个变体都没报错关键字）"
