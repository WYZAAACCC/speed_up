#!/usr/bin/env bash
# _status.sh --- 一条命令看全部长作业的进度。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t16prod.log _t13b.log _t8.log _t19H.log _t20calib.log; do
  echo "=== $f ==="
  if [ -f "$f" ]; then tail -7 "$f"; else echo '(missing)'; fi
  echo
done
echo "=== procs ==="
ps -o pid,etime,pcpu,rss,args --no-headers -C python | cut -c1-100
echo "=== mem ==="
free -g | head -2
