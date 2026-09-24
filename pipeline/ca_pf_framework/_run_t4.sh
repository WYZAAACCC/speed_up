#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _patch_t4.py
setsid nohup /root/miniconda3/envs/ml/bin/python verify_ca3d_wc_cet.py > _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log 2>&1 < /dev/null &
echo "wc_cet 已挂后台"
/root/miniconda3/envs/ml/bin/python verify_ca3d_physics.py 2>&1 | grep -E 'T4b|T4c|汇总'