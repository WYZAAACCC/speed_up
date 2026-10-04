#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 运行中算例 argv 里的 shape/nuc 相关 ==="
tr '\0' ' ' < /proc/565/cmdline | tr ' ' '\n' | grep -iE 'shape|nuc|ellip|disc'
echo
echo "=== _t5_short.py 是否透传 --nuc-shape ==="
grep -n 'nuc-shape' _t5_short.py | cut -c1-150
echo
echo "=== _bk_exp.py 的 --nuc-shape 默认值 ==="
grep -n 'nuc-shape' _bk_exp.py | cut -c1-160
echo
echo "=== 日志里「核形状」那行（最权威）==="
grep -a '核形状' _w2_t5_short_t10N160.log 2>/dev/null | tail -2 | cut -c1-200
