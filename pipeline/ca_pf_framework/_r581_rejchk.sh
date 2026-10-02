#!/bin/bash
# _r581_rejchk.sh --- ★★★ **引擎自己报的"事件被拒"计数** —— S15 的直接量化。
#
# ## 为什么要查
# R40 查明 `累计 11/5` 里的分子是 `n_ath_tgt`（**累加器**，含**被拒**的事件）。
# 而 `_bk_exp.py:2134-2135` 有一个专门的分支：
#     P('   ⚠ athermal 事件 #%d 被引擎拒（无可用空场/落位失败）@ step %d')
# ⇒ **"被拒"就是 S15 的机制本体**（`nfsv` 找不到合法空场 / 落位失败）。
# ⇒ **日志里应当能直接数出拒绝次数** —— 这比任何几何推断都直接。
cd "$(dirname "$0")" || exit 1
echo '=== ① 成功事件（`★★ **athermal 形核**`）计数 ==='
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps; do
  f="_w2_r581_p2_${t}.log"
  [ -f "$f" ] || { printf '  %-9s （无日志）\n' "$t"; continue; }
  ok=$(grep -ac 'athermal 形核' "$f")
  rej=$(grep -ac '被引擎拒' "$f")
  tot=$((ok + rej))
  printf '  %-9s 成功=%-4s **被拒=%-4s** 合计=%-4s ⇒ **拒绝率=%s**\n' \
    "$t" "$ok" "$rej" "$tot" \
    "$(awk -v r="$rej" -v t="$tot" 'BEGIN{printf (t>0? "%.1f%%" : "—"), (t>0? 100*r/t : 0)}')"
done
echo
echo '=== ② 被拒事件的行（前 12 条，带 step）==='
for t in p2_b5 p2_b3; do
  f="_w2_r581_p2_${t}.log"
  [ -f "$f" ] || continue
  echo "  ── $t ──"
  grep -a '被引擎拒' "$f" | head -12 | sed 's/^/    /'
done
echo
echo '=== ③ 成功事件里的"模式"分布（attach / fresh / stack）==='
for t in p2_b5 p2_b3; do
  f="_w2_r581_p2_${t}.log"
  [ -f "$f" ] || continue
  a=$(grep -ac '模式 \*\*attach' "$f")
  fr=$(grep -ac '模式 \*\*fresh' "$f")
  st=$(grep -ac '模式 \*\*stack' "$f")
  printf '  %-9s attach=%-4s fresh=%-4s stack=%-4s\n' "$t" "$a" "$fr" "$st"
done
echo
echo '=== 判读 ==='
echo '  · 「被拒」= `nfsv` 找不到合法空场 / 落位失败 ⇒ **就是 S15 的机制本体**'
echo '  · 拒绝率高 ⇒ 「attach 通道饱和」有**引擎自报的直接证据**（不再只是几何推断）'
