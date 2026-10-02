#!/bin/bash
# _t5_meter2.sh --- 核实 `n_lath`/`w_lath`/`a_lath` 与 `r_selfac` 的定义 + 长跑进度
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 长跑进度 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | cut -c1-70 | sed 's/^/  /'
for t in t5L62 t5L0; do
  printf '  %-6s %s\n' "$t" "$(grep -oE '\[\s*[0-9]+\]\s+Vt=[0-9.]+.*\| *[0-9.]+s/步' "_w2_t5_short_$t.log" 2>/dev/null | tail -1 | cut -c1-104)"
done
free -m | sed -n 2p | sed 's/^/  /'
echo
echo '════ ② `n_lath`/`w_lath`/`a_lath` 的定义（判据②的长宽比靠它）════'
grep -n "n_lath'\|w_lath'\|a_lath'" _bk_exp.py 2>/dev/null | head -12 | cut -c1-128 | sed 's/^/  /'
echo
echo '  ── 计算处的前后 26 行 ──'
LN=$(grep -n "n_lath=" _bk_exp.py | head -1 | cut -d: -f1)
[ -n "$LN" ] && sed -n "$((LN-24)),$((LN+4))p" _bk_exp.py | cut -c1-126 | sed 's/^/    /'
echo
echo '════ ③ `r_selfac` 的定义与值域（判据⑥靠它）════'
grep -rn 'r_selfac' _bk_measure.py windowB_surface.py _bk_exp.py 2>/dev/null | head -12 | cut -c1-128 | sed 's/^/  /'
echo
echo '  ── `_bk_measure.blocks()` 里 r_selfac 的计算段 ──'
LN2=$(grep -n 'r_selfac' _bk_measure.py 2>/dev/null | head -1 | cut -d: -f1)
[ -n "$LN2" ] && sed -n "$((LN2-18)),$((LN2+6))p" _bk_measure.py | cut -c1-126 | sed 's/^/    /'
