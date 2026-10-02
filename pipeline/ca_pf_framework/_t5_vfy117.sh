#!/bin/bash
# _t5_vfy117.sh --- ★ 验证 §117 的"被拒=3"到底是什么消息（**不只看计数**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5H3.log
echo '════ ① `被引擎拒` 的全部原文（**逐字，不截断**）════'
grep -n '被引擎拒' "$L" 2>/dev/null | sed 's/^/  /'
echo
echo '════ ② 其它形式的"拒"（防漏）════'
grep -nE '拒|拒绝|blocked|fail' "$L" 2>/dev/null \
  | grep -vE '被引擎拒|fresh` 被拒' | tail -8 | sed 's/^/  /'
echo
echo '════ ③ 与"空场/位点耗尽"直接相关的计数行（引擎自己报的）════'
grep -nE '空场|无可用|位点|sites|nofield|nocand' "$L" 2>/dev/null | tail -8 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ④ 判读（**预先写死**）════'
echo '  若 ① 的原文含"无可用空场/落位失败" ⇒ §117 的"封顶点 = m"成立'
echo '  若是别的消息 ⇒ §117 需要更正'
