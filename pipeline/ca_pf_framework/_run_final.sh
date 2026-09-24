#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== 最终回归（Step1-5 全部补丁之后）"
for f in verify_ca3d.py verify_ca3d_solute.py verify_ca3d_physics.py verify_ca3d_envelope.py; do
  s=$(date +%s)
  /root/miniconda3/envs/ml/bin/python "$f" > _audit_logs/final_$f.log 2>&1
  echo "$f rc=$? wall=$(( $(date +%s) - s ))s  $(grep -h '汇总' _audit_logs/final_$f.log | tail -1)"
done
echo "=== wc_cet 进度:"; tail -1 _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log 2>/dev/null
ps -eo pid,etime,args | grep '[v]erify_ca3d_wc' | head -1