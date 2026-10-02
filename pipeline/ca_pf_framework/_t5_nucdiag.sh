#!/bin/bash
# _t5_nucdiag.sh --- 形核事件与拒绝的计数（新跑 vs abA）
cd "$(dirname "$0")" || exit 1
echo '════ ① 新跑两臂：形核事件 / 被拒 ════'
for t in t5L62 t5L0; do
  f="_w2_t5_short_$t.log"
  [ -f "$f" ] || { echo "  $t ⚠ 无日志"; continue; }
  printf '  %-6s 形核公告=%-4s  被拒=%-4s  形核诊断行=%-3s\n' "$t" \
    "$(grep -c 'athermal 形核' "$f")" \
    "$(grep -c '被引擎拒' "$f")" \
    "$(grep -c '形核诊断已落盘' "$f")"
  echo '     ── 被拒的行（前 4）──'
  grep '被引擎拒' "$f" 2>/dev/null | head -4 | cut -c1-120 | sed 's/^/       /'
  echo '     ── 形核公告的 step 分布 ──'
  grep -oE '形核.*@ step [0-9]+' "$f" 2>/dev/null | grep -oE 'step [0-9]+' \
    | sort | uniq -c | head -6 | sed 's/^/       /'
done
echo
echo '════ ② abA：同样两项（它 step 140 有突跳 ⇒ 应有新核）════'
for f in _r445_abA.log _r426_abA.log; do
  [ -f "$f" ] || continue
  printf '  %-18s 形核公告=%-4s  被拒=%-4s\n' "$f" \
    "$(grep -c 'athermal 形核' "$f")" "$(grep -c '被引擎拒' "$f")"
  echo '     ── 形核公告的 step 分布（前 8）──'
  grep -oE '形核.*@ step [0-9]+' "$f" 2>/dev/null | grep -oE 'step [0-9]+' \
    | sort -t' ' -k2 -n | uniq -c | head -8 | sed 's/^/       /'
done
echo
echo '════ ③ 新跑的形核诊断 JSON（若已落盘）════'
for t in t5L62 t5L0; do
  j="_exp/_bk_t5/dry_$t/nuc_dbg.json"
  [ -f "$j" ] && { echo "  ── $t ──"; head -c 600 "$j" | sed 's/^/     /'; echo; }
done
