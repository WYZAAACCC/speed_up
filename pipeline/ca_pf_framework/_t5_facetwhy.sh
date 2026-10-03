#!/bin/bash
# _t5_facetwhy.sh --- ★★★★★ 为什么 `facet-proj=1` 让形状变圆/变厚（读实现）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `facet_project()` 的定义位置与 docstring ════'
grep -n "def facet_project" windowB_surface.py | sed 's/^/  /'
LN=$(grep -n "def facet_project" windowB_surface.py | head -1 | cut -d: -f1)
[ -n "$LN" ] && sed -n "$LN,$((LN+42))p" windowB_surface.py | sed 's/^/  /'
echo
echo '════ ② `--facet-proj` 的 CLI 说明（**它到底该做什么**）════'
sed -n '3898,3916p' _bk_exp.py | sed 's/^/  /'
echo
echo '════ ③ 它在引擎里被调用处（条件）════'
grep -n "facet_project\|facet_proj" _bk_exp.py | sed 's/^/  /' | cut -c1-150
