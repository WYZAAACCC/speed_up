#!/bin/bash
# _r581_qs.sh --- 准静态钟（1B）的**收敛档**进度：还要跑多久？什么时候自停？
cd "$(dirname "$0")" || exit 1
for t in p2_b5 p2_b3; do
  L="_w2_r581_p2_${t}.log"
  [ -f "$L" ] || { echo "  $t：（无日志）"; continue; }
  echo "=== $t ==="
  echo "  ── 已收敛的档（[qs] 行）──"
  grep -a "\[qs\]" "$L" 2>/dev/null | tail -8 | sed 's/^/    /'
  n=$(grep -ac "\[qs\].*收敛" "$L" 2>/dev/null)
  echo "  ⇒ 收敛档数 = $n"
  echo "  ── 最后一行 ──"
  tail -1 "$L" | cut -c1-150 | sed 's/^/    /'
  echo "  ── 形核事件 / 被拒 ──"
  grep -ac "形核" "$L" 2>/dev/null | sed 's/^/    含"形核"的行数 = /'
  echo
done
echo "=== 判读 ==="
echo "  · goal 预估：每档 ~100 步、共 ~5 档 ⇒ 500–600 步自停"
echo "  · ⚠ 若 [qs] 行里出现"达到 T_end"或"步数用尽"就是终态"
grep -a "T_end\|步数用尽\|自停\|stop" _w2_r581_p2_p2_b5.log _w2_r581_p2_p2_b3.log 2>/dev/null | tail -4 | sed 's/^/    /'
