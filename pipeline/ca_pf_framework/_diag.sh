#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== procs total ==="
ps -e --no-headers | wc -l
echo "=== python ==="
pgrep -a python | cut -c1-80
echo "=== mem ==="
free -g | head -2
echo "=== log tails ==="
for f in _t16prod.log _t13b.log _t24rve.log _t21.log _t11j_after_a1a2.log; do
  echo "--- $f"
  if [ -f "$f" ]; then
    grep -v -e RuntimeWarning -e 'self.reinitialize' -e 'g.advance(' "$f" | tail -5
  else
    echo '(missing)'
  fi
done
