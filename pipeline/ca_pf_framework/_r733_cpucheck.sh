#!/usr/bin/env bash
# _r733_cpucheck.sh —— 确认长 A/B 进程的**核亲和**（R630 C1/C4：必须逐线程实测验证）。
set -uo pipefail
echo "=== 主进程 ==="
for P in $(pgrep -f '[_]bk_exp.py'); do
  echo "pid=$P  etime=$(ps -o etime= -p $P | tr -d ' ')"
  grep -E 'Cpus_allowed_list|Threads' /proc/$P/status 2>/dev/null | sed 's/^/    /'
done
echo
echo "=== 该进程树内**所有线程**的核亲和（去重）==="
for P in $(pgrep -f '[_]bk_exp.py'); do
  for T in /proc/$P/task/*; do
    cat $T/status 2>/dev/null | grep -H Cpus_allowed_list | sed "s|/proc/$P/task/||;s|/status:Cpus_allowed_list:||"
  done
done | sort | uniq -c | sort -rn | head -8
