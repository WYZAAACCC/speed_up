#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 引擎构造 kw（第 854 行附近）'
sed -n '848,900p' _bk_exp.py
echo
echo '=== df / elastic 相关'
grep -nE "df_const|df_start|elastic_driving|'df'|\"df\"|ed=|ed_" _bk_exp.py | head -20
