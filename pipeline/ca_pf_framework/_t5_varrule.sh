#!/bin/bash
# _t5_varrule.sh --- 查 `--var-rule` 的实现：什么条件下才会选到**第二个变体**？
cd "$(dirname "$0")" || exit 1
echo '════ ① CLI 定义与取值 ════'
grep -n "add_argument('--var-rule'" _bk_exp.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ② `var_rule` 在引擎里怎么用 ════'
grep -n 'var_rule' windowB_surface.py 2>/dev/null | sed 's/^/  /'
echo
echo '════ ③ 选择逻辑的上下文（**不截断行**）════'
LN=$(grep -n "var_rule" windowB_surface.py 2>/dev/null | grep -v 'def \|#' | head -1 | cut -d: -f1)
echo "  （起点 = $LN）"
[ -n "$LN" ] && sed -n "$((LN-6)),$((LN+28))p" windowB_surface.py | sed 's/^/  /'
