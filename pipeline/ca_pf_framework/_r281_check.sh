#!/bin/bash
# _r281_check.sh —— 查 `_r280` 到底起没起、起了几个。
cd "$(dirname "$0")" || exit 1
echo "=== 所有 _bk_exp.py 进程 ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  fp=$(printf '%s' "$cl" | grep -o 'facet-proj [0-9]*' | tail -1)
  printf '  pid=%-7s tag=%-14s %s\n' "$p" "${tag:-?}" "${fp:-（无 facet-proj）}"
done
echo "  （总数 $(pgrep -fc '_bk_exp[.]py' || echo 0)）"
echo
echo "=== _r280 相关文件 ==="
ls -la _w2_r280* 2>/dev/null || echo "  (无)"
echo
echo "=== 两个新臂的产物 ==="
for d in saSet2P0 saSet2F2P0; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-16s rows=%-4s last=%s\n' "$d" "$(wc -l < "$f")" \
      "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-16s (无 series.csv)\n' "$d"
  fi
  [ -d "_exp/_bk_mb/dry_$d" ] && echo "     目录在：$(ls -1 _exp/_bk_mb/dry_$d | tr '\n' ' ')"
done
echo
echo "=== emit 日志（确认重建成功）==="
for s in saSet2 saSet2F2; do
  f="_w2_r280_${s}_emit.log"
  [ -f "$f" ] && { printf '  %s: %s 行\n' "$f" "$(wc -l < "$f")"; \
    grep -m1 'miniconda3' "$f" | tail -c 200; echo; }
done
