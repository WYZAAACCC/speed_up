#!/usr/bin/env bash
# _r545_wait.sh —— 轮询等周期播种 A/B 结束，然后打印对照读数
set -u
cd "$(dirname "$0")"
for i in $(seq 1 40); do
  n=$(pgrep -f 'tag ps_b' | wc -l)
  if [ "$n" -eq 0 ]; then
    echo "（第 $i 次轮询：已无 ps_b* 进程）"
    break
  fi
  sleep 60
done
echo
bash _r545_readps.sh
