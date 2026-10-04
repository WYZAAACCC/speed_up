#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== CSV 写入的刻度表 / 列定义 ==="
grep -n 'SCALE\|_scale\|1e17\|1e18\|1e9\|_FMT\|fmt' _bk_exp.py | head -20 | cut -c1-175
echo
echo "=== csv 写出那一行 ==="
grep -n 'csvf.write\|writerow\|_COLS\|column' _bk_exp.py | head -14 | cut -c1-175
echo
echo "=== 表头与列名定义处（含 Vt）==="
grep -n "'Vt'" _bk_exp.py | cut -c1-175
