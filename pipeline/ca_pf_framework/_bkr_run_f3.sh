#!/bin/bash
# _bkr_run_f3.sh —— 在 WSL 里跑 F3 有效迁移率实验（输出直接到 stdout）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
exec /root/miniconda3/envs/ml/bin/python -u _bkr_f3.py
