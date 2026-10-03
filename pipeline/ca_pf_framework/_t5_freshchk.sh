#!/bin/bash
# _t5_freshchk.sh --- ★★★★★ 两臂的 **fresh 通道**是否已触发（④⑤ 的直接前兆）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5N276 t5NR; do
  echo "════ $t ════"
  L1=_w2_t5_n276.log      # t5N276 的引擎日志
  L2=_w2_t5_nr_engine.log # t5NR 的引擎日志
  [ "$t" = "t5N276" ] && L=$L1 || L=$L2
  [ -f "$L" ] || { echo "  （无 $L）"; continue; }
  echo '  ── 形核事件按模式统计（attach / stack / **fresh**）──'
  grep -oE '模式 \*\*[a-z]+\*\*' "$L" 2>/dev/null | sort | uniq -c | sed 's/^/     /'
  echo '  ── 含 fresh 的行（若有）──'
  grep -nE 'fresh' "$L" 2>/dev/null | tail -4 | cut -c1-150 | sed 's/^/     /'
  echo "      （fresh 行数 = $(grep -c fresh "$L" 2>/dev/null || echo 0)）"
  echo '  ── 形核公告总数 ──'
  printf '     athermal 形核 公告数 = %s\n' "$(grep -c 'athermal 形核' "$L" 2>/dev/null || echo 0)"
  echo
done
echo '════ 判据 ════'
echo '  * 若 `fresh` 已出现 ⇒ ④⑤ 的**前提**已启动，接下来只看是否落在**不同变体**上;'
echo '  * 若仍未出现 ⇒ 需继续等（先前经验：首个 fresh 在**事件 24-25**，而事件按 n(T_end)=23 的节奏）;'
echo '  * ★ `t5NR`（random）的 fresh 应给出 **不同**变体；`t5N276`（ed）的 fresh 会给**同一**变体。'
