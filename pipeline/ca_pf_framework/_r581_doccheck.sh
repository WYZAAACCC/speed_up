#!/bin/bash
# _r581_doccheck.sh --- ★ 交付物完整性自查（R581 收尾用）
#   检查：① 六份文档都在、② 行数、③ 关键数字在文档间**是否一致**、④ 快照数
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── ① 六份核心文档 ──'
for f in R581_TASK5_VERDICT.md R581_FINAL_SUMMARY.md R581_SIMPLIFICATION_AUDIT.md \
         R581_PENDING_DECISIONS.md R581_DISCIPLINES.md R581_TASK5_PREREQ_RECHECK.md \
         OPOPT_LEDGER.md; do
  if [ -f "$f" ]; then
    printf '  %-34s %6s 行  %8s 字节\n' "$f" "$(wc -l < "$f")" "$(stat -c%s "$f")"
  else
    printf '  %-34s ⚠ 不存在\n' "$f"
  fi
done
echo
echo '── ② 关键数字在各文档里的出现次数（**不一致就说明有文档没更新**）──'
for pat in '19.5 GB' '23.5 GB' 'm=37' 'm ≥ 46' 'V × m' '0.5 × V' 'B ≈ 28' 'B ≥ 110' 'nslab=13' '13 根'; do
  printf '  %-12s' "$pat"
  for f in R581_TASK5_VERDICT.md R581_FINAL_SUMMARY.md R581_PENDING_DECISIONS.md; do
    n=$(grep -c -- "$pat" "$f" 2>/dev/null)
    printf ' %s=%s' "$(echo "$f" | sed 's/R581_//;s/\.md//')" "$n"
  done
  echo
done
echo
echo '── ③ AGENTS.md 预算 ──'
A=/mnt/f/speed_up/AGENTS.md
if [ -f "$A" ]; then
  S=$(stat -c%s "$A")
  printf '  AGENTS.md = %s 字节（预算 65536）⇒ %s\n' "$S" \
    "$([ "$S" -lt 65536 ] && echo '✅ 在预算内' || echo '❌ 超预算')"
fi
echo
echo '── ④ 快照数（一个都不能少）──'
printf '  _r580_backup/ 下目录数 = %s\n' "$(ls -d _r580_backup/*/ 2>/dev/null | wc -l)"
printf '  最新 3 个：\n'
ls -dt _r580_backup/*/ 2>/dev/null | head -3 | sed 's/^/    /'
echo
echo '── ⑤ 已落盘的臂（N=64 与 N=160）──'
printf '  N=64 臂目录：%s\n' "$(ls -d _exp/_bk_mn64/dry_* 2>/dev/null | wc -l)"
ls -d _exp/_bk_mn64/dry_* 2>/dev/null | sed 's|.*/dry_|    |' | tr '\n' ' '; echo
printf '  N=160 臂目录：%s\n' "$(ls -d _exp/_bk_p2/dry_* 2>/dev/null | wc -l)"
