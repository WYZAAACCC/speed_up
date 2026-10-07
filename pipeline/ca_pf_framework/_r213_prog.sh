#!/bin/bash
# _r213_prog.sh —— 通用进度：任意臂的行数 + 末步 + 进程数 + 内存。
cd "$(dirname "$0")" || exit 1
echo "=== 指定臂的进度 ==="
for d in "$@"; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-14s rows=%-4s last_step=%s\n' "$d" "$(wc -l < "$f")" \
      "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-14s (还没有 series.csv)\n' "$d"
  fi
done
echo
echo "=== 标签下最近开跑的臂（按 mtime）==="
ls -dt _exp/_bk_mb/dry_* 2>/dev/null | head -5 | while read -r p; do
  printf '  %-34s %s\n' "$(basename "$p")" "$(stat -c %y "$p" | cut -d. -f1)"
done
echo
echo "=== 进程 ==="
pgrep -fc '_bk_exp[.]py' || echo "  0"
echo "=== 内存 (MB) ==="
free -m | head -2
echo
echo "=== _r210 日志尾 ==="
tail -5 _w2_r210.log 2>/dev/null
