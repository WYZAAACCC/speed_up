#!/bin/bash
# _bk_remeasure.sh <npz...>  —— 在**落盘状态**上重量（验证"量具有 bug 也能事后重测"）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for f in "$@"; do
  echo "=== $f ==="
  "$PY" -u _bk_measure.py --npz "$f" 2>&1 \
    | grep -a -E 'vol_|ncomp_1|nslab|nf3|nseg|box_touch|^  [nwa]_[12]|nreg_used|runs|M '
done
