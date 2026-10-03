#!/bin/bash
# _t5_readdf.sh --- ★★★★★★ 查 `self.df` 的**按场取值** —— 判"化学驱动力差"是否恒等于 0
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `self.df` / `.df =` 的赋值处（全部）════'
grep -nE '\.df *=|self\.df|df *= *np\.|drive_of_T' windowB_surface.py 2>/dev/null | head -24 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `_bk_exp.py` 里 df 的相关赋值 ════'
grep -nE '\.df|df *=|drive_of_T|df_vec' _bk_exp.py 2>/dev/null | head -20 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ③ `drive_of_T` 的定义 ════'
L=$(grep -n 'def drive_of_T' windowB_surface.py windowB_km.py _bk_exp.py 2>/dev/null | head -1 | cut -d: -f2)
F=$(grep -ln 'def drive_of_T' windowB_surface.py windowB_km.py _bk_exp.py 2>/dev/null | head -1)
if [ -n "$L" ] && [ -n "$F" ]; then
  echo "  （$F 第 $L 行起）"
  sed -n "${L},$((L+16))p" "$F" | nl -ba -v"$L" | cut -c1-150
else
  echo '  ⚠ 没找到 def drive_of_T'
fi
echo
echo '════ ④ 有没有"按变体给 df"的地方（`df` 是数组的证据）════'
grep -nE 'df\[0\]|df\[k|df *= *np\.(full|array|zeros)|df *= *\[' windowB_surface.py _bk_exp.py 2>/dev/null | head -14 | cut -c1-160 | sed 's/^/  /'
