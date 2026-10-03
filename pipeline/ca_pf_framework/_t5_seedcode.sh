#!/bin/bash
# _t5_seedcode.sh --- ★★★★★ 第2步：读代码，看一个新场被放**几个种子**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `attach` / `stack` 形核时调用的种子函数 ════'
grep -n "attach\|stack" _bk_exp.py | grep -iE "seed|plate|nuc" | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② `seed_plate` 的**定义**（看它撒 1 个还是多个核）════'
grep -n "def seed_plate" _bk_exp.py windowB_surface.py windowB_pf3d.py windowB_km.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ③ `seed_plate` 函数体（前 60 行）════'
F=$(grep -ln "def seed_plate" _bk_exp.py windowB_surface.py windowB_pf3d.py windowB_km.py 2>/dev/null | head -1)
if [ -n "$F" ]; then
  L=$(grep -n "def seed_plate" "$F" | head -1 | cut -d: -f1)
  echo "  （文件 $F，第 $L 行起）"
  sed -n "${L},$((L+60))p" "$F" | nl -ba -v"$L" | cut -c1-150 | sed 's/^/  /'
else
  echo '  ⚠ 没找到 seed_plate'
fi
