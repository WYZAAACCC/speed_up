#!/bin/bash
# _r284_state.sh —— 汇总状态：文档、进程、各臂步数、p45L/P 末态。
cd "$(dirname "$0")" || exit 1
echo "=== 文档 ==="
wc -l R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md
for f in R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md; do
  n=$(tr -cd '\t' < "$f" | wc -c)
  echo "  $f 制表符 = $n"
done
echo
echo "=== 摘要的节标题（末尾 4 个）==="
grep -n '^## [0-9]*\.' AUDIT_SUMMARY_R76.md | tail -4
echo
echo "=== 进程 ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  fp=$(printf '%s' "$cl" | grep -o 'facet-proj [0-9]*' | tail -1 | sed 's/facet-proj //')
  printf '  pid=%-7s tag=%-14s facet-proj=%s\n' "$p" "${tag:-?}" "${fp:-?}"
done
echo
echo "=== 各臂步数 ==="
for d in p45L p45P p45L0 p45P0 saSet2P0 saSet2F2P0 saSet2EDV; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-14s step=%s\n' "$d" "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-14s (未开始)\n' "$d"
  fi
done
echo
echo "=== _r225 收尾日志 ==="
tail -6 _w2_r225.log 2>/dev/null
echo
echo "=== 负载 ==="
cat /proc/loadavg | cut -d' ' -f1-3
free -m | head -2 | sed 's/^/  /'
