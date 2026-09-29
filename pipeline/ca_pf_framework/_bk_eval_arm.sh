#!/usr/bin/env bash
# _bk_eval_arm.sh —— 对若干臂一次跑完：同类性对照表 + V-7 成对记账 + 完整判决
# 用法: bash _bk_eval_arm.sh <dir> [dir...]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "################ 1. 同类性对照表"
"$PY" _bk_cmp.py "$@"
for A in "$@"; do
  echo
  echo "################ 2. 成对界面记账 + V-7/V-7b：$A"
  "$PY" _bk_pair.py "$A" 2>&1 | grep -E 'V-7|覆盖率|^snap_|Σ 单根宽面|实测 Σ|间隙|夹层 β'
done
