#!/bin/bash
# _r273_orphan.sh —— 查 `_r272` 超时后有没有**残留进程**（`AGENTS.md §3.11` 的坑）。
cd "$(dirname "$0")" || exit 1
echo "=== _bk_exp.py 进程数 ==="
n=$(pgrep -fc '_bk_exp[.]py' || true)
echo "  ${n:-0}"
echo
echo "=== 逐个进程：pid / etime / tag / cwd ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  tag=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -o 'tag [A-Za-z0-9_]*' | tail -1)
  cwd=$(readlink "/proc/$p/cwd" 2>/dev/null)
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '  pid=%-7s etime=%-9s %-14s cwd=%s\n' "$p" "${et:-?}" "${tag:-?}" "${cwd:-?}"
done
echo
echo "=== _r272 的产物/日志 ==="
ls -la _w2_r272*.log 2>/dev/null | head -8 || echo "  (无日志)"
for t in th1 th2 th4 th8 th2b; do
  f="_exp/_bk_thr/dry_$t/series.csv"
  if [ -f "$f" ]; then
    printf '  %-6s rows=%-4s last=%s\n' "$t" "$(wc -l < "$f")" \
      "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-6s (无 series.csv)\n' "$t"
  fi
done
echo
echo "=== _r272 主日志尾部 ==="
tail -20 _w2_r272.log 2>/dev/null || echo "  (无 _w2_r272.log)"
