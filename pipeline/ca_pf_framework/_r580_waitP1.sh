#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for _ in $(seq 1 "${1:-14}"); do
  sleep 55
  grep -q 'DONE' _w2_r580_p1verify.log 2>/dev/null && break
done
cat _w2_r580_p1verify.log
