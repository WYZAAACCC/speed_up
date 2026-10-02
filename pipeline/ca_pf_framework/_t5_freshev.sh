#!/bin/bash
# _t5_freshev.sh --- ★ 找"第一个 fresh 事件"的**直接证据**（模式标记）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5H3.log
echo '════ ① 形核事件里的**模式**分布（逐字）════'
grep -oE '模式 \*\*[a-z]+\*\*' "$L" 2>/dev/null | sort | uniq -c | sed 's/^/  /'
echo
echo '════ ② 形核事件行（末 8 条，**不截断**）════'
grep 'athermal 形核' "$L" 2>/dev/null | tail -8 | sed 's/^/  /'
echo
echo '════ ③ 与 fresh 有关的**计数行**（引擎自己报的）════'
grep -nE 'fresh|n_fresh|待机位点|fresh_blocked|fresh_cand' "$L" 2>/dev/null \
  | grep -vE '^\s*[0-9]+:\s*#' | tail -10 | sed 's/^/  /'
echo
echo '════ ④ 对照：abA 的模式分布（它有多块）════'
for f in _r445_abA.log _r426_abA.log; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -oE '模式 \*\*[a-z]+\*\*' "$f" 2>/dev/null | sort | uniq -c | sed 's/^/     /'
done
