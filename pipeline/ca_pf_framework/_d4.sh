#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t13b.log _t16prod.log _t24rve.log _t21g.log; do
  echo "===== $f"
  if [ -f "$f" ]; then
    grep -vE 'RuntimeWarning|self\.reinitialize|WindowB|g\.advance' "$f" | tail -"${1:-12}"
  else
    echo '(missing)'
  fi
  echo
done
echo "===== procs"
pgrep -c python
free -g | head -2
