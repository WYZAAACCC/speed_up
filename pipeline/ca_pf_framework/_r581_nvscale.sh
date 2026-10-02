#!/bin/bash
# _r581_nvscale.sh --- 启动 nv/N 标度测量（绑核 0-3，避免与车道抢核）
# 用法: bash _r581_nvscale.sh
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "[$(date '+%F %T')] 启动 _r581_nvscale.py（taskset 0-3）"
taskset -c 0-3 "$PY" -u _r581_nvscale.py
echo "[$(date '+%F %T')] 结束 rc=$?"
