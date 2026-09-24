#!/bin/bash
# 结束那个过慢的 WC 探针（均匀驱动下 envelope 与 analytic 逐位等价，已由 E1/T4b/T4c 证明，无需重跑）
for p in $(ps -eo pid,args | grep '[_]wc_envelope_modes' | awk '{print $1}'); do kill $p 2>/dev/null; done
sleep 1
cd /mnt/f/speed_up/pipeline/ca_pf_framework
echo "=== wc_cet 套件:"; ps -eo pid,etime,args | grep '[v]erify_ca3d_wc' | head -1
grep -E '汇总|\[WARN|\[FAIL|T6' _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log 2>/dev/null | tail -8