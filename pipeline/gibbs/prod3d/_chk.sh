#!/bin/bash
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
ls -l stage1_meltpool_*k*.i 2>/dev/null
echo "=== gen logs ==="
for f in /tmp/gen_k*.log; do
  echo "--- $f"
  tail -6 "$f"
done
