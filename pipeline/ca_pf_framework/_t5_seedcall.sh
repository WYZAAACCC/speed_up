#!/bin/bash
# _t5_seedcall.sh --- ★★★★★ 查 `seed_plate` 的**所有调用点**：同一个场 k 会不会被多次播种？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `seed_plate(` 的全部调用点（含上下文行号）════'
grep -n "seed_plate(" _bk_exp.py windowB_surface.py windowB_pf3d.py windowB_km.py 2>/dev/null \
  | grep -v "def seed_plate" | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ② `attach` 通道的实现处（看它循环几次）════'
grep -n "attach" windowB_surface.py 2>/dev/null | grep -viE "^\s*#" | head -20 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ③ 形核函数 `def nucleate` 的位置 ════'
grep -n "def nucleate" windowB_surface.py windowB_pf3d.py _bk_exp.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ④ 若找到 `def nucleate`，打印它的**循环结构**（缩进层级 + 含 seed 的行）════'
F=windowB_surface.py
L=$(grep -n "def nucleate" "$F" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  echo "  （$F 第 $L 行起；下面列出该函数内**缩进较浅的行**以看清循环骨架）"
  awk -v s="$L" 'NR>=s && NR<=s+220' "$F" \
    | grep -nE "^        (for |while |if |elif |else|def )|seed_plate|attach|stack|n_seed|sites" \
    | head -40 | cut -c1-150 | sed 's/^/  /'
else
  echo '  （没找到 def nucleate）'
fi
