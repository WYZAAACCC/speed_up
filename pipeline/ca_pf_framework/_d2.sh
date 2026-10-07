#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t16prod.log _t13b.log _t24rve.log _t21.log; do
  echo "=== $f"
  if [ -f "$f" ]; then
    grep -v -e 'RuntimeWarning' -e 'self.reinitialize' -e 'g.advance(' "$f" | tail -7
  else
    echo '(missing)'
  fi
  echo
done
echo "=== procs ==="
pgrep -a python | cut -c1-48
free -g | head -2
