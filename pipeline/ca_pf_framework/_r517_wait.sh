#!/usr/bin/env bash
# R517 —— 等 abA 跑完（轮询，最多 ~10 分钟）
set -u
cd "$(dirname "$0")"
for i in $(seq 1 12); do
  S=$(tail -1 _exp/_bk_mb/dry_abA/series.csv | cut -d, -f1)
  printf '[%s] step=%s\n' "$(date +%H:%M:%S)" "$S"
  if [ "$S" -ge 5922 ]; then echo "DONE"; break; fi
  sleep 50
done
echo "--- 进程 ---"
ps -eo pid,etimes,args | grep '[_]bk_exp' | cut -c1-46
echo "--- abA 目录 ---"
ls -1 _exp/_bk_mb/dry_abA/ | sed 's/[0-9]\+/N/g' | sort -u
