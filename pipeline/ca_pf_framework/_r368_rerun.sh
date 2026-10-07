#!/usr/bin/env bash
# _r368_rerun.sh -- 用**修正后的掩码**（与 m_ok 相交）重跑三臂的 §174
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
for A in "saSet2F2P0 400" "saSet2 200" "permB1_200 200"; do
  echo "################################ $A"
  $PY -u _r358_ed_offline.py $A 2>&1 | grep -vE 'systemd user session|\[WindowB\]'
done
