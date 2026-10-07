#!/bin/bash
# _t5_ms1200.sh --- 里程碑：snap_01200 是否到（到则跑预测2）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
date '+NOW = %F %T'
if [ -f _exp/_bk_t5/dry_t5H3/snap_01200.npz ]; then
  echo '  ⇒ snap_01200 **到** ⇒ 跑预测 2'
  taskset -c 16-19 /root/miniconda3/envs/ml/bin/python _t5_fillts.py 2>&1 | tail -12
else
  echo "  ⇒ snap_01200 **未到**（t5H3 末步 = $(tail -1 _exp/_bk_t5/dry_t5H3/series.csv 2>/dev/null | cut -d, -f1)）"
fi
