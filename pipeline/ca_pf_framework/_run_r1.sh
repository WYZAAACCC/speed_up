#!/usr/bin/env bash
# _run_r1.sh --- R1 reinit 审计的统一启动器（**按需改 ARG**）
# 用法： bash _run_r1.sh <脚本名> <日志名> [超时秒]
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
S="${1:?script}"
L="${2:?log}"
T="${3:-1500}"
echo "[_run_r1] script=$S log=$L timeout=${T}s  $(date '+%F %T')" > "$L"
timeout --signal=KILL "$T" /root/miniconda3/envs/ml/bin/python -u "$S" >> "$L" 2>&1
RC=$?
echo "[_run_r1] RC=$RC  $(date '+%F %T')" >> "$L"
exit $RC
