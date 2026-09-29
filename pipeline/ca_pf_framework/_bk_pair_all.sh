#!/usr/bin/env bash
# _bk_pair_all.sh —— 对若干算例跑成对界面记账（V-7）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
for A in "$@"; do
  echo "############################################################ $A"
  "$PY" _bk_pair.py "$A" 2>&1 | grep -E 'V-7|覆盖率|Σ 单根|实测 Σ|间隙|^  [0-9 ]|板条[0-9]|当量|无 β|步|^={10}|^snap'
done
