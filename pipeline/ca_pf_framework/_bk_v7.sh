#!/usr/bin/env bash
# _bk_v7.sh —— 只打印各臂的 V-7 / V-7b 判决（成对界面记账）
# 用法: bash _bk_v7.sh <dir> [dir...]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
for A in "$@"; do
  echo "#### $A"
  "$PY" _bk_pair.py "$A" 2>&1 | grep -E 'V-7|覆盖率|^snap_|Σ 单根宽面|间隙'
done
