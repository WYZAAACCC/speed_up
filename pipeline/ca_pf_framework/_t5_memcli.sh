#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _r579_report.py 的 CLI ==="
grep -n 'add_argument\|sys.argv\|^N =\|^N=' _r579_report.py | head -20 | cut -c1-170
echo
echo "=== 它的构型来源（是否是固定的 N=160 四构型）==="
grep -n 'N *= *160\|160\|cfg\|NFG\|prec' _r579_report.py | head -20 | cut -c1-170
