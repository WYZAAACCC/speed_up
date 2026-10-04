#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 引擎构造横幅里的几何（最权威，直接打印的）==="
grep -aE 'R_nuc|t_nuc|elong|板条|椭球|nucleus|几何|L_lath|W_lath|T_lath' \
  _w2_t5_short_t5ETAo.log 2>/dev/null | head -14 | cut -c1-185
echo
echo "=== _t5_short.py 实际传给引擎的几何参数 ==="
grep -n "plate-L\|plate-W\|plate-T\|eng-r-nm\|eng-elong\|eng-t-nm" _t5_short.py | cut -c1-165
echo
echo "=== _bk_exp.py 里核几何怎么由这些算出来 ==="
sed -n '1590,1600p;1640,1650p;1780,1790p' _bk_exp.py | cut -c1-165
