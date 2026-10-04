#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 所有 nuc_fresh_every / nuc-fresh-every 出现处 ==="
grep -n 'nuc_fresh_every\|nuc-fresh-every\|_K_exp' _bk_exp.py _t5_short.py | cut -c1-175
echo
echo "=== _bk_exp.py 1120-1200（硬校验区）==="
sed -n '1120,1200p' _bk_exp.py | cut -c1-150
