#!/bin/bash
# _r319_chk318.sh —— 专查 `_r318`（框架级单变量实验）是否起来、跑了多少。
cd "$(dirname "$0")" || exit 1
echo "=== _w2_r318.log ==="
[ -f _w2_r318.log ] && cat _w2_r318.log || echo "  (不存在)"
echo
echo "=== _w2_r318_emit.log 末尾（重建命令是否拿到）==="
[ -f _w2_r318_emit.log ] && tail -3 _w2_r318_emit.log || echo "  (不存在)"
echo
echo "=== 两个新臂的目录/行数 ==="
for t in edNear edFar; do
  d="_exp/_bk_mb/dry_$t"
  if [ -d "$d" ]; then
    if [ -f "$d/series.csv" ]; then
      printf '  %-8s rows=%-4s last=%s\n' "$t" "$(wc -l < "$d/series.csv")" \
        "$(tail -1 "$d/series.csv" | cut -d, -f1)"
    else
      printf '  %-8s (目录在，无 series.csv)\n' "$t"
    fi
  else
    printf '  %-8s (无目录)\n' "$t"
  fi
done
echo
echo "=== 运行日志行数 ==="
for f in _w2_r318_edNear_run.log _w2_r318_edFar_run.log; do
  [ -f "$f" ] && printf '  %-32s %s 行, 最新步=%s\n' "$f" "$(wc -l < "$f")" \
    "$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')" \
    || printf '  %-32s (不存在)\n' "$f"
done
echo
echo "=== 所有 _bk_exp.py 进程的 tag ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  printf '  pid=%-7s %s\n' "$p" \
    "$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1)"
done
echo "  （共 $(pgrep -fc '_bk_exp[.]py' || echo 0) 个）"
