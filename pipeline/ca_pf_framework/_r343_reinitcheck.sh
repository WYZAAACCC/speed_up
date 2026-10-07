#!/usr/bin/env bash
# _r343_reinitcheck.sh -- 从臂自己的日志里核实"reinit 到底跑了没有"
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log \
         _w2_r322_near200_run.log _w2_r322_mid200_run.log _w2_r322_far200_run.log; do
  [ -f "$f" ] || continue
  echo "=== $f ==="
  echo "  'pair reinit' 出现次数: $(grep -c 'pair reinit' "$f" || true)"
  echo "  'reinit' 出现次数:      $(grep -c 'reinit' "$f" || true)"
  echo "  'Traceback' :           $(grep -c 'Traceback' "$f" || true)"
  echo "  '跳过'/'skip' :          $(grep -c 'skip' "$f" || true)"
  grep -m3 -n 'reinit' "$f" | head -3
  echo
done
echo "=== 归档臂对照（400 步跑的日志）==="
for f in _w2_r165_saSet2_run.log _w2_r165_run.log _w2_r240.log; do
  [ -f "$f" ] && { echo "--- $f: pair reinit × $(grep -c 'pair reinit' "$f" || true)"; }
done
ls _w2_r165*.log 2>&1 | head
