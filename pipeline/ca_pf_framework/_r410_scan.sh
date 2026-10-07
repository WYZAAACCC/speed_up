#!/bin/bash
# _r410_scan.sh —— 在多个 step 上跑 `_r410_fpmech.py`（机理直测的跨步复核）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
RUN=${1:-_exp/_bk_mb/dry_saSet2}
shift || true
STEPS=${*:-"0 20 100 400"}
for S in $STEPS; do
  echo "################ STEP $S ################"
  timeout 1800 "$PY" _r410_fpmech.py "$RUN" "$S" 2>&1 \
    | sed -n '/^\[1\] 基线/,$p'
done
