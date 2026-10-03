#!/bin/bash
# _t5_amwait200.sh --- 等 t5AM_* 到 step ≥200，然后跑**按步对齐**对照
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for i in $(seq 1 60); do          # 最多 60 × 30 s = 30 min
  S=$(tail -1 _exp/_bk_t5/dry_t5AM_ell/series.csv 2>/dev/null | cut -d, -f1)
  if [ -n "$S" ] && [ "$S" -ge 200 ] 2>/dev/null; then break; fi
  A=$(ps -eo args --no-headers 2>/dev/null | grep -c 'dry_t5AM_ell')
  [ "$A" -eq 0 ] && { echo "⚠ t5AM_ell 进程消失"; break; }
  sleep 30
done
echo "NOW = $(date '+%F %T')   t5AM_ell 末步 = $(tail -1 _exp/_bk_t5/dry_t5AM_ell/series.csv 2>/dev/null | cut -d, -f1)"
echo
$PY _t5_amcmp.py 2>&1 | head -30
