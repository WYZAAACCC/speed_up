#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t13b.log _t16prod.log _t24rve.log; do
  echo "== $f"
  if [ -f "$f" ]; then
    grep -E '心跳|^  [0-9]|采样|block|packet|RVE' "$f" 2>/dev/null | tail -5
  else
    echo '(missing)'
  fi
done
echo "== procs"
pgrep -a python | cut -c1-40
free -g | head -2
