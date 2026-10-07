#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== _bk_exp.py 里与驱动/弹性/带宽有关的开关'
grep -nE "add_argument" _bk_exp.py | grep -iE "df|el|band|const|elastic|noel" | head -14
echo
echo '=== 引擎侧引用点'
grep -nE "df_const|self\.pf|PF3D|elastic|extend|band" _bk_exp.py | head -20
