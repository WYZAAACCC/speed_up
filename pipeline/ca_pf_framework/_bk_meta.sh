#!/usr/bin/env bash
# _bk_meta.sh —— 列出算例目录 + 打印 meta.json（避免在 PowerShell 里拼引号）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for R in "$@"; do
  echo "######## LIST $R"
  "$PY" _bk_meta.py --list "$R"
done
