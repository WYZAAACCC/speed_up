#!/bin/bash
# _bk_launch.sh <logname> <script.py> [args...]  —— 语法检查 + 后台启动 + 落盘日志
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
LOGNAME=$1; shift
SCRIPT=$1; shift
"$PY" -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read()); print('syntax OK:',sys.argv[1])" "$SCRIPT" || exit 9
LOG=/mnt/f/speed_up/pipeline/ca_pf_framework/$LOGNAME
setsid nohup "$PY" -u "$SCRIPT" "$@" > "$LOG" 2>&1 < /dev/null &
echo "started pid=$! log=$LOG"
