#!/bin/bash
# _t5_readdG.sh --- ★★★★★★ 读 `dG_cell`（界面局部驱动力）—— 判它是否含**曲率项**、能否变负
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `dG_cell` 的全部出现处 ════'
grep -n 'dG_cell' windowB_surface.py | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② `dG_cell` 的定义上下文（前后各 22 行）════'
L=$(grep -n 'dG_cell *=' windowB_surface.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L - 22)); E=$((L + 16))
  echo "  （第 ${S}–${E} 行）"
  sed -n "${S},${E}p" windowB_surface.py | nl -ba -v"$S" | cut -c1-152
fi
