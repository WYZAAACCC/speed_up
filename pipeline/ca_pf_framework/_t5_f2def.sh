#!/bin/bash
# _t5_f2def.sh --- ★ `f2_faces` 的确切定义（F2 是什么）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `f2_faces` 在哪个文件里被算出来 ════'
grep -rn "f2_faces" *.py 2>/dev/null | head -8 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ② 它的定义段（**不截断**，前后各 22 行）════'
F=$(grep -rln "f2_faces" *.py 2>/dev/null | head -1)
LN=$(grep -n "f2_faces" "$F" 2>/dev/null | head -1 | cut -d: -f1)
echo "  （文件 = $F，起点 = $LN）"
[ -n "$LN" ] && sed -n "$((LN-22)),$((LN+4))p" "$F" | sed 's/^/  /'
echo
echo '════ ③ F2 / F3 的命名注释（找"F2"的解释）════'
grep -rn "'F2'\|\"F2\"\|F2 =\|F2面\|F2 面" *.py 2>/dev/null | head -8 | cut -c1-150 | sed 's/^/  /'
