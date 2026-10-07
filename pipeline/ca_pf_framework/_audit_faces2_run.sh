#!/bin/bash
# _audit_faces2_run.sh --- 顺序跑两档（避免同时起两个重作业，见 AGENTS §3.12）
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=6
PY=/root/miniconda3/envs/ml/bin/python
$PY _audit_faces2.py --reinit 0  --nstep 160
$PY _audit_faces2.py --reinit 25 --nstep 160
echo ALL_DONE
