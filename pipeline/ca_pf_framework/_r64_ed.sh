#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== advance 的签名里有没有 ed'
sed -n '2847,2858p' windowB_surface.py
echo
echo '=== advance 内部 ed / dG_cell 的来源'
grep -nE "ed_cell|edk|dG_cell =|elastic_driving\(\)|self\.pf" windowB_surface.py | sed -n '1,20p'
echo
echo '=== _bk_exp 调 advance 时传了什么'
grep -nE "g\.advance\(" -A 8 _bk_exp.py | head -14
