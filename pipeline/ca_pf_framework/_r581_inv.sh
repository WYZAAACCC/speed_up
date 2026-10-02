#!/bin/bash
# _r581_inv.sh --- 交付物清单：保险/快照/报告/量具 到底有哪些（**不猜，直接列**）
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T') 交付物清单 ==="
echo "--- 1. 快照（_r580_backup/）---"
if [ -d _r580_backup ]; then
  for d in _r580_backup/*/; do
    n=$(ls "$d" 2>/dev/null | wc -l)
    ts=$(stat -c %y "$d" 2>/dev/null | cut -c1-19)
    printf '  %-46s %2s 个文件  %s\n' "$(basename "$d")" "$n" "$ts"
  done
else
  echo "  ❌ 没有 _r580_backup/ 目录"
fi
echo "--- 2. 保险脚本 ---"
for f in _r580_snapshot.sh _r580_rollback.sh _r580_rollback_test.sh; do
  if [ -f "$f" ]; then printf '  ✅ %-28s %s 行\n' "$f" "$(wc -l < "$f")";
  else printf '  ❌ %-28s 缺\n' "$f"; fi
done
echo "--- 3. BASELINE.md ---"
if [ -f BASELINE.md ]; then echo "  ✅ 存在（$(wc -l < BASELINE.md) 行）"
else echo "  ❌ **不存在** —— goal 成功判据② 要求「基线快照 + SHA256SUMS + BASELINE.md」"; fi
echo "--- 4. R581 报告 ---"
for f in R581_OPOPT_L1L2.md R581_TASK5_PREREQ_RECHECK.md R581_TASK5_INTERIM.md \
         R581_SIMPLIFICATION_AUDIT.md R581_TASK5_VERDICT.md R581_PENDING_DECISIONS.md; do
  if [ -f "$f" ]; then printf '  ✅ %-34s %4s 行\n' "$f" "$(wc -l < "$f")";
  else printf '  ❌ %-34s 缺\n' "$f"; fi
done
echo "--- 5. R581 量具脚本 ---"
for f in _r581_c6judge.py _r581_c3mis.py _r581_c5budget.py _r581_frag.py \
         _r581_p2read.py _r581_cols.py _r581_lanes.sh _r581_now.sh _r581_ps.sh; do
  if [ -f "$f" ]; then printf '  ✅ %-24s %4s 行\n' "$f" "$(wc -l < "$f")";
  else printf '  ❌ %-24s 缺\n' "$f"; fi
done
echo "--- 6. 判据②的"实测回滚一次"留档 ---"
ls -1 _w2_r581_rollback*.log _w2_r580_rollback*.log 2>/dev/null | sed 's/^/  /' || echo "  （找 _w2_*rollback*.log）"
grep -l "T1\|T3\|通过" _w2_*rollback*.log 2>/dev/null | sed 's/^/  留档：/'
