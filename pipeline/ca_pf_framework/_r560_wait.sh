#!/usr/bin/env bash
# _r560_wait.sh —— 等 soft 内存量具跑完并打印
set -u
cd "$(dirname "$0")"
for i in $(seq 1 25); do
  n=$(pgrep -f '_r560_softmem' | wc -l)
  [ "$n" -eq 0 ] && { echo "（第 $i 次轮询：已结束）"; break; }
  sleep 30
done
echo
tail -42 _w2_r560_run.log
