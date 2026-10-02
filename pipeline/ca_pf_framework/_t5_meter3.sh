#!/bin/bash
# _t5_meter3.sh --- 坐实 `mm['n_k']`/`w_k`/`a_k` 到底是哪三个方向 + 长跑进度
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① `n_%d` / `w_%d` / `a_%d` 的计算点 ════'
grep -n "'n_%d'\|\"n_%d\"\|n_%d" _bk_measure.py 2>/dev/null | head -10 | cut -c1-126 | sed 's/^/  /'
echo
LN=$(grep -n "'n_%d'" _bk_measure.py | head -1 | cut -d: -f1)
echo "  （首个引用行 = ${LN:-未找到}）"
[ -n "$LN" ] && sed -n "$((LN-30)),$((LN+6))p" _bk_measure.py | cut -c1-124 | sed 's/^/    /'
echo
echo '════ ② 定义文档（docstring 里的 n/w/a）════'
grep -n 'extent\|厚度\|长度\|宽度\|法向\|normal' _bk_measure.py 2>/dev/null | head -14 | cut -c1-124 | sed 's/^/  /'
echo
echo '════ ③ 长跑进度 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | cut -c1-56 | sed 's/^/  /'
for t in t5L62 t5L0; do
  printf '  %-6s: %s\n' "$t" "$(grep -oE '\[\s*[0-9]+\]\s+Vt' "_w2_t5_short_$t.log" 2>/dev/null | tail -1)"
done
free -m | sed -n 2p | sed 's/^/  /'
