#!/usr/bin/env bash
# _r557_wait.sh —— 等用时包线量具跑完并打印
set -u
cd "$(dirname "$0")"
for i in $(seq 1 40); do
  n=$(pgrep -f '_r557_timebudget' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已结束）"; break; }
  sleep 60
done
echo
sed -n '16,50p' _w2_r557_run.log
