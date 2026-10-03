#!/bin/bash
# _t5_readfcrit.sh --- ★★★★★ 读 `use_fcrit` 分支的判据式（判它是否含 `df` 与曲率）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `use_fcrit` / `_fcrit` 的全部出现处 ════'
grep -nE 'use_fcrit|_fcrit|nuc_fcrit' windowB_surface.py _bk_exp.py 2>/dev/null | head -20 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ② 判据式所在处（含 `df` 与 `4*gamma` 的行）════'
grep -nE '4 *\* *self\.gamma|4\*gamma|4 \* gamma|gamma.*t\b.*>|> *4' windowB_surface.py 2>/dev/null | head -10 | cut -c1-165 | sed 's/^/  /'
echo
echo '════ ③ `def nucleate` 的签名与判据段 ════'
L=$(grep -n 'def nucleate' windowB_surface.py | head -1 | cut -d: -f1)
echo "  （第 $L 行起）"
sed -n "${L},$((L+18))p" windowB_surface.py | nl -ba -v"$L" | cut -c1-155
echo
echo '════ ④ 判据实际计算处（搜 fcrit 附近的表达式）════'
grep -n 'fcrit' windowB_surface.py | head -12 | cut -c1-165 | sed 's/^/  /'
