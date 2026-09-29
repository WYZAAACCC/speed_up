#!/bin/bash
# _bk_prog.sh <tag> —— 精度检查：生产臂是否真的在推进
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=${1:-p2}
date +%H:%M:%S
for a in dry wet gneg gpos; do
  d="_exp/_bk_block/${a}_${TAG}"
  f="_w2_blk_${a}_${TAG}.log"
  [ -d "$d" ] || continue
  n=$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)
  last=$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)
  mt=$(ls -la --time-style=+%H:%M:%S "$d/series.csv" 2>/dev/null | awk '{print $6}')
  sz=$(du -sh "$d" 2>/dev/null | cut -f1)
  echo "$a: series行=$n  末step=$last  csv改于=$mt  目录=$sz"
done
echo "--- vmstat (si/so 应为 0) ---"
vmstat 2 2 | tail -1
free -m | head -2
