#!/bin/bash
# _t5_capgen.sh --- 查补池的"代次上限" _cap_gen 与相关计数（形核停滞的决定性参数）
cd "$(dirname "$0")" || exit 1
echo '════ ① _cap_gen 的定义与取值 ════'
grep -n '_cap_gen\|cap_gen' windowB_surface.py 2>/dev/null | head -14 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ② sites_margin / sites_refilled 的定义与默认 ════'
grep -n 'sites_margin\|sites_refilled' windowB_surface.py _bk_exp.py 2>/dev/null | head -14 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ③ 驱动层传了哪些（我的启动器）════'
grep -n 'sites-refill\|sites_margin\|sites-refill' _t5_short.py 2>/dev/null | cut -c1-120 | sed 's/^/  /'
echo
echo '════ ④ 新跑日志里与位点/形核诊断有关的行 ════'
for t in t5L62 t5L0; do
  f="_w2_t5_short_$t.log"
  printf '  ── %s ──\n' "$t"
  grep -nE '位点|sites|refill|补池|fresh_|nocand|空场' "$f" 2>/dev/null | head -8 | cut -c1-126 | sed 's/^/     /'
done
echo
echo '════ ⑤ nuc_dbg.json 有没有落盘（含 fresh_* 归因计数）════'
for t in t5L62 t5L0; do
  j="_exp/_bk_t5/dry_$t/nuc_dbg.json"
  [ -f "$j" ] && { echo "  ✅ $j"; head -c 500 "$j" | sed 's/^/     /'; echo; } \
              || echo "  ⏳ $t：nuc_dbg.json 未落盘（跑完才写）"
done
