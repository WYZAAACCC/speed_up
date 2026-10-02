#!/bin/bash
# _r581_bg2diag.sh --- BG2 为什么慢（对比 BK6）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
for t in BG2 BK6 BK7; do
  f="_w2_r581_blk_${t}.log"
  [ -f "$f" ] || { echo "  $t：无日志"; continue; }
  rej=$(grep -c '被引擎拒' "$f" 2>/dev/null || echo 0)
  nuc=$(grep -c 'athermal 形核' "$f" 2>/dev/null || echo 0)
  rows=$(wc -l < "_exp/_bk_blk/dry_${t}/series.csv" 2>/dev/null || echo 0)
  printf '  %-5s 日志 %-9s 字节 | 被拒 %-6s 形核 %-6s | series 行数 %s\n' \
    "$t" "$(stat -c%s "$f" 2>/dev/null)" "$rej" "$nuc" "$rows"
done
echo
echo '── BG2 日志尾 4 行 ──'
tail -4 _w2_r581_blk_BG2.log 2>/dev/null | cut -c1-104 | sed 's/^/  /'
echo
echo '── BG2 的 seeds/首行（种子尺寸线索）──'
head -2 _exp/_bk_blk/dry_BG2/series.csv 2>/dev/null | cut -c1-140 | sed 's/^/  /'
echo
echo '── 在跑的臂 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '  tag=%-9s 时长=%s\n' "${tag:-?}" "$et"
done
