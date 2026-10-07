#!/bin/bash
# _r312_chk311.sh —— 查 `_r311`（§146 第二构型检验）是否起来了。
cd "$(dirname "$0")" || exit 1
echo "=== _w2_r311.log ==="
if [ -f _w2_r311.log ]; then
  cat _w2_r311.log
else
  echo "  (不存在)"
fi
echo
echo "=== 进程列表 ==="
for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
  cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
  printf '  pid=%-7s tag=%s\n' "$p" "${tag:-?}"
done
echo "  （共 $(pgrep -fc '_bk_exp[.]py' || echo 0) 个）"
echo
echo "=== mb2fp10EDV 目录 ==="
d=_exp/_bk_mb/dry_mb2fp10EDV
if [ -d "$d" ]; then
  ls -1 "$d" | tr '\n' ' '; echo
  [ -f "$d/series.csv" ] && echo "  rows=$(wc -l < "$d/series.csv")" \
    && tail -1 "$d/series.csv" | cut -d, -f1
else
  echo "  (尚未创建)"
fi
echo
echo "=== _r311_run.log 尾部 ==="
tail -5 _w2_r311_run.log 2>/dev/null || echo "  (不存在)"
