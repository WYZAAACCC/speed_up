#!/bin/bash
# _t5_readv.sh --- ★★★★★ 读界面速度 `v_cell` 的表达式与驱动力来源
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `v_cell` 的全部出现处 ════'
grep -n 'v_cell' windowB_surface.py _bk_exp.py 2>/dev/null | head -24 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② `v_cell` 的定义上下文（前后 20 行）════'
L=$(grep -n 'v_cell *=' windowB_surface.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L - 20)); E=$((L + 18))
  echo "  （windowB_surface.py 第 ${S}–${E} 行）"
  sed -n "${S},${E}p" windowB_surface.py | nl -ba -v"$S" | cut -c1-150
else
  echo '  ⚠ windowB_surface.py 里没找到 `v_cell =`'
fi
