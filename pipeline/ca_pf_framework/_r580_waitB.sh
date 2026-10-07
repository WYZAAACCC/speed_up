#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for _ in $(seq 1 "${1:-9}"); do
  sleep 55
  grep -q 'BISECT DONE' _w2_r580_bisect_run.log 2>/dev/null && break
done
tail -32 _w2_r580_bisect_run.log
