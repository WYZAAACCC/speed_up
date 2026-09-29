#!/bin/bash
# _bk_run_smoke.sh —— 启动 F3 判决实验（后台、绝对路径日志）
#   ⚠ 不要用 `pkill -f _bk_smoke_f3.py` 停它 —— 那会杀掉调用它的 shell（AGENTS §3.10）。
#     按 PID 杀：ps -e -o pid,cmd | grep _bk_smoke
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
LOG=${LOG:-/mnt/f/speed_up/pipeline/ca_pf_framework/_w2_f3smoke2.log}
setsid nohup "$PY" -u _bk_smoke_f3.py "$@" > "$LOG" 2>&1 < /dev/null &
echo "started pid=$! log=$LOG"
