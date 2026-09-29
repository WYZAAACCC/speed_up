#!/bin/bash
# _bk_peek.sh <tag> —— 看所有生产臂的进度（不含 PowerShell 引号地狱）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=${1:-p2}
free -m | head -2
echo "-----"
for a in dry wet gneg gpos g0; do
  f="_w2_blk_${a}_${TAG}.log"
  [ -f "$f" ] || continue
  echo "== $a =="
  grep -a -E '构造|播种|余量|dt=|\] |Traceback|Error|判决' "$f" | tail -3 | cut -c1-150
done
