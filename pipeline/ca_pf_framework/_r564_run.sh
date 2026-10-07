#!/bin/bash
# _r564_run.sh --- 在 WSL 侧找到"生产用的那个解释器"并跑同一份基准。
# 为什么要有这个脚本：PowerShell 直接拼 `wsl -e bash -lc "…引号…"` 会被吞引号
# （AGENTS §3.9 / ENVIRONMENT），所以一律落成 .sh 再执行。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

echo "### conda envs ###"
ls -d /root/miniconda3/envs/*/bin/python 2>/dev/null

for PY in /root/miniconda3/envs/ml/bin/python \
          /root/miniconda3/envs/moose/bin/python \
          /root/miniconda3/bin/python; do
  if [ -x "$PY" ]; then
    echo ""
    echo "########## WSL: $PY ##########"
    "$PY" _r564_env.py 2>&1 | tail -25
  fi
done
