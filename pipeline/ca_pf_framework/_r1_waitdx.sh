#!/bin/bash
# 等 Δx 一致性对照跑完，自动重算 `_r1_dxconsist.py`
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1dxtest.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

while true; do
  c=$(pgrep -c -f "_r1_exp.py --out _exp/mid192_s2_ns4" 2>/dev/null)
  [ -z "$c" ] && c=0
  [ "$c" = "0" ] && break
  sleep 60
done
log "mid192_s2_ns4 结束"
$PY -u _r1_dxconsist.py >> "$LOG" 2>&1
log "Δx 一致性重算完成"
