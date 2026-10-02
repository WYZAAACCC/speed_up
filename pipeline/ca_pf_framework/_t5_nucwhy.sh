#!/bin/bash
# _t5_nucwhy.sh --- 定位"无可用空场/落位失败"的两个分支
cd "$(dirname "$0")" || exit 1
echo '════ ① 拒绝信息的来源（在驱动层还是引擎）════'
grep -n '无可用空场\|落位失败' _bk_exp.py windowB_surface.py 2>/dev/null | cut -c1-130 | sed 's/^/  /'
echo
echo '════ ② 引擎侧：nucleate() 里"落位"相关的返回 ════'
grep -n 'def nucleate' windowB_surface.py | cut -c1-120 | sed 's/^/  /'
LN=$(grep -n 'def nucleate' windowB_surface.py | head -1 | cut -d: -f1)
echo "  （nucleate 起点 = $LN）"
echo
echo '  ── nucleate 里出现 return / 失败 / site 的行（相对行号）──'
awk -v s="$LN" 'NR>=s && NR<=s+260 && (/return/ || /site/ || /fail/ || /oob/ || /空场/ || /no_room/ || /fresh/)' \
  windowB_surface.py | head -40 | cut -c1-124 | sed 's/^/    /'
