#!/bin/bash
# 汇报消融 A/B 与求解器扫描的进度。写成文件跑，避免 Git Bash 吞 $t 之类的循环变量。
echo "现在 $(date '+%H:%M:%S')   MOOSE 进程数=$(pgrep -c phase_field-opt)"
echo
echo "################ 消融 A/B ################"
for t in C v0 v1 v2 v3; do
  f="/root/work/s1d_ab/$t/run.log"
  echo "--- $t ---"
  if [ ! -f "$f" ]; then echo "   未开始"; continue; fi
  printf "   收敛步=%s  线性求解次数=%s  大小=%s\n" \
    "$(grep -ac 'Solve Converged' "$f")" \
    "$(grep -ac 'Linear solve' "$f")" \
    "$(stat -c %s "$f")"
  echo "   逐变量残差:"
  grep -a -A12 "individual variables" "$f" | tail -12 | sed 's/^/     /'
  echo "   线性求解状态:"
  grep -a "Linear solve" "$f" | sed 's/^ *//' | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
  grep -a -m2 -E '\*\*\* ERROR|zero pivot|Singular' "$f" | sed 's/^/     /'
done

echo
echo "################ 求解器扫描 ################"
cat /root/work/ts.log
for t in s1_hypre s2_hybrid s3_lu s4_asm; do
  f="/root/work/s1d_w/$t.log"
  [ -f "$f" ] || continue
  echo "--- $t ---"
  printf "   收敛步=%s  线性求解次数=%s\n" \
    "$(grep -ac 'Solve Converged' "$f")" "$(grep -ac 'Linear solve' "$f")"
  grep -a "Linear solve" "$f" | sed 's/^ *//' | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
  grep -a -m2 -E '\*\*\* ERROR|zero pivot|Singular|out of memory' "$f" | sed 's/^/     /'
done
