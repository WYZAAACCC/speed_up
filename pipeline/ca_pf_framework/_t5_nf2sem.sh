#!/bin/bash
# _t5_nf2sem.sh --- ★ 查 `nf2` 的**确切语义**（回到产出它的代码）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `nf2` 在引擎里的定义处 ════'
grep -n 'nf2' _bk_exp.py | head -14 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ② 它周围的计算段（**不截断**）════'
LN=$(grep -n 'nf2' _bk_exp.py | grep -E '=|def ' | head -1 | cut -d: -f1)
echo "  （起点 = $LN）"
[ -n "$LN" ] && sed -n "$((LN-14)),$((LN+8))p" _bk_exp.py | sed 's/^/  /'
echo
echo '════ ③ 与它同族的量（nf3 / nf3_col）在代码里的注释 ════'
grep -n 'nf3\|nf2' _bk_exp.py | grep -E '#|"""' | head -8 | cut -c1-150 | sed 's/^/  /'
