#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
if ps -p 869 > /dev/null 2>&1; then echo "wc_cet 仍在跑: $(ps -o etime= -p 869)"; else echo "wc_cet 已结束"; fi
grep -E '汇总|\[WARN|\[FAIL' _audit_logs/after_fix1/verify_ca3d_wc_cet.py.log 2>/dev/null | tail -6