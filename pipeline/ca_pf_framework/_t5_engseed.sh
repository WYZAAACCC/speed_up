#!/bin/bash
# _t5_engseed.sh --- 核实 `--eng-seed` 旋钮确实存在（并更正我上一轮的 A22 记述）
cd "$(dirname "$0")" || exit 1
echo '════ ① `--eng-seed` 的 argparse 定义 ════'
grep -n "eng-seed\|eng_seed" _bk_exp.py 2>/dev/null | head -14 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ② 它最终传给 nuc_cfg 的那一行 ════'
grep -n 'seed=a.eng_seed\|seed=int' _bk_exp.py 2>/dev/null | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ③ 实跑时它出现在命令行里吗（看长跑的日志/命令）════'
grep -oE '\-\-eng-seed [0-9]+' _w2_t5_short_t5L62.log 2>/dev/null | head -3 | sed 's/^/  长跑日志: /'
echo "  （空 = 长跑没传 ⇒ 用默认值）"
echo
echo '════ ④ 默认值是多少 ════'
sed -n "$(grep -n "add_argument('--eng-seed" _bk_exp.py | head -1 | cut -d: -f1),+4p" _bk_exp.py \
  2>/dev/null | cut -c1-124 | sed 's/^/  /'
