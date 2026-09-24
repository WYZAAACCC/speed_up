#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/_audit_logs/after_fix1
echo "=== 文件:"
ls -la
echo; echo "=== verify_ca3d_physics.py 的 WARN/FAIL 上下文:"
grep -n -B6 -A3 'WARN' verify_ca3d_physics.py.log | head -40
echo; echo "=== 基线里对应项（16 PASS）:"
grep -n 'T4b\|T4c\|WARN' ../baseline/verify_ca3d_physics.py.log | head -20