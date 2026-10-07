#!/bin/bash
# _r264_docs.sh —— 文档与作业的最终核对。
cd "$(dirname "$0")" || exit 1
echo "=== 文档 ==="
wc -l R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md
echo
echo "=== 制表符计数（应全为 0）==="
for f in R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md; do
  n=$(tr -cd '\t' < "$f" | wc -c)
  echo "  $f : $n"
done
echo
echo "=== 台账新增节 ==="
grep -n '^## §1[34][0-9]' R30_AUDIT_LEDGER.md | tail -12
echo
echo "=== 摘要新增节 ==="
grep -n '^## [0-9]*\.' AUDIT_SUMMARY_R76.md | tail -6
echo
echo "=== 作业进度 ==="
for d in saSet2DT saOddGDT p45L p45P p45L0 p45P0 saSet2EDV; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-12s step=%s\n' "$d" "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-12s (未开始)\n' "$d"
  fi
done
echo "  procs=$(pgrep -fc '_bk_exp[.]py' || echo 0) ; load=$(cut -d' ' -f1 /proc/loadavg)"
free -m | head -2 | sed 's/^/  /'
