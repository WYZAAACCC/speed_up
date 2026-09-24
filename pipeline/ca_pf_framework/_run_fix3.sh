#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _verify_fix3.py
echo; echo "=== 后台套件进度:"
cat _audit_logs/after_fix1_suite.out 2>/dev/null