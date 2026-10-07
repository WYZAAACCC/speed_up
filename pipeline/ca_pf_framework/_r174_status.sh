#!/bin/bash
# _r174_status.sh —— 查 R165 的两个 λ=1 臂的进度与进程状态（不杀任何东西）。
cd "$(dirname "$0")" || exit 1
echo "=== ① _exp/_bk_mb 下带 F2 的目录 ==="
ls -d _exp/_bk_mb/*F2* 2>/dev/null || echo "    (无匹配)"
echo
echo "=== ② 各目录内容 ==="
for d in _exp/_bk_mb/*F2*; do
  [ -d "$d" ] || continue
  echo "-- $d"
  ls -la "$d" 2>/dev/null | head -10
done
echo
echo "=== ③ 相关进程 ==="
ps -eo pid,etime,pcpu,rss,args --sort=-pcpu 2>/dev/null | grep -E '_bk_exp' | grep -v grep | head -8
echo
echo "=== ④ R165 的两个臂在 series.csv 上的行数与末步 ==="
for d in dry_saSet2F2 dry_saOddGF2; do
  f="_exp/_bk_mb/$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-14s rows=%-6s last_step=%s\n' "$d" "$(wc -l < "$f")" "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-14s (series.csv 不存在)\n' "$d"
  fi
done
echo
echo "=== ⑤ _r165 的 stdout 日志尾部 ==="
for f in _w2_r165*.log _r165*.log; do
  [ -f "$f" ] && { echo "-- $f"; tail -12 "$f"; }
done
echo
echo "=== ⑥ 内存 ==="
free -g | head -2
