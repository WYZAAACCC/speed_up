#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== mm 的装配函数 ==="
grep -n "def .*mm\|mm = \|return mm\|_thick\|thickness" _bk_exp.py | head -20 | cut -c1-175
echo
echo "=== 跨文件找 n_k 的定义 ==="
grep -rn "n_%d" windowB_km.py windowB_surface.py 2>/dev/null | head -12 | cut -c1-175
echo
echo "=== measure/geom 函数 ==="
grep -n "^def \|^    def " _bk_exp.py | awk -F: '$1>2700 && $1<3000' | cut -c1-140
