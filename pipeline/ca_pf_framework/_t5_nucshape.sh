#!/bin/bash
# _t5_nucshape.sh --- ★★★★★ 查清：**当前用的形核核到底是什么形状**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `--nuc-shape` 的定义与取值 ════'
grep -n "add_argument('--nuc-shape'" _bk_exp.py | cut -c1-170 | sed 's/^/  /'
grep -n "nuc_shape\|'--nuc-shape'" _bk_exp.py | head -8 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ② `nuc_cfg` 的 `shape` 参数怎么用（**决定实际形状**）════'
grep -n "shape" windowB_surface.py | grep -iE "disc|ellip|plate|def |if |==" | head -14 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ③ `--eng-elong` 的定义与说明（**与 shape 的关系**）════'
sed -n '3790,3800p' _bk_exp.py | sed 's/^/  /'
echo
echo '════ ④ 我启动器实际传的参数（**逐字**）════'
grep -n "nuc-shape\|eng-elong\|plate-" _t5_short.py | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ⑤ 运行横幅里**与形状有关的所有行** ════'
for t in t5H3; do
  grep -nE "核形状|elong|plate_L|plate_W|plate_T|圆盘|长条|椭球" _w2_t5_short_$t.log 2>/dev/null | head -10 | cut -c1-150 | sed 's/^/  /'
done
