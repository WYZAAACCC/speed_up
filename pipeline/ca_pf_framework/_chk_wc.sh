#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== wc_cet 状态:"; ps -eo pid,etime,args | grep '[v]erify_ca3d_wc' | head -1
echo "--- 日志:"; grep -E '汇总|\[WARN|\[FAIL' _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log 2>/dev/null | tail -6
echo; echo "=== 优化后快速回归:"
for f in verify_ca3d.py verify_ca3d_envelope.py; do
  /root/miniconda3/envs/ml/bin/python "$f" > /tmp/q_$f.log 2>&1
  echo "$f rc=$? $(grep -h '汇总' /tmp/q_$f.log | tail -1)"
done