#!/bin/bash
# _r576_regress.sh --- 跑归档路径的逐位回归（`_r30_regress.sh`），并把旧日志归档改名。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _w2_r30_regress.log _w2_r30_regress_stdout.log; do
  if [ -f "$f" ]; then cp -f "$f" "$f.r575arch"; echo "  已归档 $f -> $f.r575arch"; fi
done
echo "=== R576 REGRESS START $(date '+%F %T') ==="
bash _r30_regress.sh > _w2_r576_regress_run.log 2>&1
echo "=== R576 REGRESS DONE rc=$? $(date '+%F %T') ==="
grep -nE '共有列逐位一致|差异|FAIL|PASS|ALL PASS|windowB_pf3d' _w2_r576_regress_run.log | tail -30
