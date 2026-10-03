#!/bin/bash
# _t5_plateL.sh --- ★★★★★ 核查 `plate_L/W/T` 是什么（是否 = 初始种子尺寸 ⇒ 我测的"长度"其实是种子）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `plate_L` 的定义与注释（**回到产出它的代码**，第 21 条纪律）════'
grep -n "plate_L\|plate_W\|plate_T" _bk_exp.py windowB_surface.py 2>/dev/null | head -14 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ② 它的注释段（**不截断**）════'
LN=$(grep -n "plate_L" windowB_surface.py 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$LN" ]; then
  F=windowB_surface.py
else
  F=_bk_exp.py; LN=$(grep -n "plate_L" _bk_exp.py | head -1 | cut -d: -f1)
fi
echo "  （文件 = $F，起点 = $LN）"
[ -n "$LN" ] && sed -n "$((LN-18)),$((LN+6))p" "$F" | sed 's/^/  /'
echo
echo '════ ③ 我实测的板条尺寸（§84/§144）对照 ════'
echo '  实测长度 910–1227 nm  ｜ plate_L = 1000 nm'
echo '  实测宽度 442–619 nm   ｜ plate_W =  500 nm'
echo '  实测厚度 229–326 nm   ｜ plate_T =  510 nm'
echo '  ⇒ **长度/宽度几乎逐数吻合种子盘** ⇒ 强烈提示"没长大、只是种子"'
