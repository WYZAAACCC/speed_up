#!/bin/bash
# _t5_freshwhy.sh --- ★ `fresh` 被拒的**原因**（读 `:2696` 附近的完整上下文）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5H3.log
echo '════ ① 「fresh 被拒」那一行的完整上下文（前后各 6 行，**不截断**）════'
LN=$(grep -n 'fresh` 被拒' "$L" 2>/dev/null | head -1 | cut -d: -f1)
echo "  （行号 = $LN）"
[ -n "$LN" ] && sed -n "$((LN-6)),$((LN+6))p" "$L" | sed 's/^/  /'
echo
echo '════ ② 日志里与"投递点/位点/守卫"有关的行（末 12）════'
grep -nE '投递点|位点|sites|守卫|cover|落位|空场|no_field' "$L" 2>/dev/null \
  | tail -12 | sed 's/^/  /'
echo
echo '════ ③ 引擎的机制实现处（找打印这句的代码）════'
grep -n 'fresh` 被拒\|退回 `stack`' _bk_exp.py windowB_surface.py 2>/dev/null | sed 's/^/  /'
