#!/bin/bash
# _r581_fallback.sh --- ★★★★★★ 取 `fresh` 被拒的直接证据（退回 `stack` 的计数）
#   代码逐字（`_bk_exp.py:2073-2082`）：
#     # ★ 记账（不静默）：要 `fresh` 却被挡（待机位点用尽 / 落位失败）
#     #   ⇒ 当场退回 `stack`，并把退回**计数**（`meta` 里查得到）。
#     P('   ⚠ athermal 事件 #%d：`fresh` 被拒 ⇒ **退回 `stack`**（本算例累计 %d 次）')
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '################ ① 日志里的「`fresh` 被拒 ⇒ 退回 `stack`」################'
for T in A B C D E F G; do
  f="_w2_r581_mn64_${T}.log"
  [ -f "$f" ] || f="_w2_r581_mn64${T}.log"
  [ -f "$f" ] || continue
  n=$(grep -c 'fresh` 被拒' "$f" 2>/dev/null)
  printf '  %-3s 出现 %s 次' "$T" "$n"
  if [ "${n:-0}" -gt 0 ]; then
    printf '   末一条：'
    grep 'fresh` 被拒' "$f" | tail -1 | cut -c1-68
  else
    echo
  fi
done
echo
echo '################ ② `meta.json` / `nuc_dbg.json` 里的退回计数 ################'
for T in A B C D E F G; do
  for f in "nuc_dbg.json" "meta.json"; do
    p="_exp/_bk_mn64/dry_${T}/${f}"
    [ -f "$p" ] || continue
    v=$(grep -o '"n_fresh_fallback"[^,}]*' "$p" 2>/dev/null | head -1)
    w=$(grep -o '"n_fresh"[^,}]*' "$p" 2>/dev/null | head -1)
    [ -n "$v$w" ] && printf '  %-3s %-14s %s  %s\n' "$T" "$f" "$v" "$w"
  done
done
echo
echo '################ ③ 形核通道的代码逻辑（逐字）################'
sed -n '2052,2057p' _bk_exp.py | cut -c1-96 | sed 's/^/  /'
