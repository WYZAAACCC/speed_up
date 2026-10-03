#!/bin/bash
# _t5_readel.sh --- ★★★★★★ 读 `elastic_driving()`（弹性能项 `ed` 的定义与符号）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `def elastic_driving` 的位置 ════'
grep -n 'def elastic_driving' windowB_surface.py | cut -c1-140 | sed 's/^/  /'
echo
L=$(grep -n 'def elastic_driving' windowB_surface.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L - 30)); E=$((L + 55))
  echo "════ ② 函数体与前置注释（第 ${S}–${E} 行）════"
  sed -n "${S},${E}p" windowB_surface.py | nl -ba -v"$S" | cut -c1-155
fi
