#!/usr/bin/env bash
# _r331_prog2.sh -- 看清每个臂目录里到底有什么文件
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb
for n in saSet2P0 saSet2F2P0 near200 mid200 far200; do
  echo "### $n"
  ls -la "$D/$n" 2>&1 | head -20
done
echo "### logs tail"
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _w2_r280.log _w2_r322.log; do
  echo "--- $f ---"
  ls -la "$f" 2>&1
  tail -6 "$f" 2>&1
done
