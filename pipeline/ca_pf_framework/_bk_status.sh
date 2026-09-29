#!/usr/bin/env bash
# _bk_status.sh —— 进程 + 轨迹 一起看
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
bash _bk_alive.sh
echo
/root/miniconda3/envs/ml/bin/python _bk_traj.py
