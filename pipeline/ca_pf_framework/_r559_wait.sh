#!/usr/bin/env bash
# _r559_wait.sh —— 等剖析跑完并打印
set -u
cd "$(dirname "$0")"
for i in $(seq 1 30); do
  n=$(pgrep -f '_r559_profile' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已结束）"; break; }
  sleep 30
done
echo
cat _w2_r559_run.log | tail -60
