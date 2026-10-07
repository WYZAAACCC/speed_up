#!/usr/bin/env bash
# _r342_armlog.sh -- 看两个 P0 臂自己的 run.log 进度
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  echo "=== $f ($(wc -l < "$f" 2>/dev/null || echo 0) 行) ==="
  tail -3 "$f" 2>&1
  echo
done
echo "=== 200 步臂日志 ==="
ls -la _w2_r322*.log 2>&1 | head
for f in _w2_r322_near200.log _w2_r322_mid200.log _w2_r322_far200.log; do
  [ -f "$f" ] && { echo "--- $f ---"; tail -2 "$f"; }
done
echo
echo "=== CPU ==="
ps -eo pid,etimes,times,pcpu,rss,comm --sort=-times | head -8
