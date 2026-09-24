#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
for i in $(seq 1 40); do
  if ! ps -p 869 > /dev/null 2>&1; then break; fi
  sleep 30
done
echo "=== wc_cet 结果:"
grep -E '汇总|\[WARN|\[FAIL' _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log | tail -8