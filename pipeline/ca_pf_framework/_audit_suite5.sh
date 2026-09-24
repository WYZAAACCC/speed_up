#!/bin/bash
L=/mnt/f/speed_up/pipeline/ca_pf_framework/_audit_logs/verify_ca3d_wc_cet.py.log
grep -nE '汇总|\[WARN|\[FAIL|\(FAIL' "$L" | head -10
echo "--- 末 20 行:"
tail -20 "$L"