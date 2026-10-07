#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "===== T21 (beta sweep) ====="
awk '/T21-2/,0' _t21.log | tail -20
echo
echo "===== procs ====="
ps -o pid,etime,pcpu,rss,args --no-headers -C python | cut -c1-72
free -g | head -2
