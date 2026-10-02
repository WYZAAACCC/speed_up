#!/bin/bash
# _r581_p2data.sh --- 被杀的 N=160 臂：**数据还在哪、到哪一步**
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 找 p2_m12 / p2_m12b 的产物目录 ──'
for base in _exp _exp/_bk_n160 _exp/_bk_p2; do
  [ -d "$base" ] || continue
  for d in "$base"/dry_p2_m12 "$base"/dry_p2_m12b; do
    [ -d "$d" ] || continue
    n=$(wc -l < "$d/series.csv" 2>/dev/null)
    st=$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)
    ns=$(ls "$d" 2>/dev/null | grep -c '^snap_')
    printf '  %-34s step=%-7s 行=%-6s 快照=%-4s 字节=%s\n' \
      "$d" "$st" "$n" "$ns" "$(stat -c%s "$d/series.csv" 2>/dev/null)"
  done
done
echo
echo '── 兜底：全盘找 dry_p2_m12* ──'
find _exp -maxdepth 3 -type d -name 'dry_p2_m12*' 2>/dev/null | while read -r d; do
  printf '  %-40s step=%-7s 行=%s\n' "$d" \
    "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)" \
    "$(wc -l < "$d/series.csv" 2>/dev/null)"
done
echo
echo '── 臂 L 的终态（被杀时）──'
d=_exp/_bk_mn64/dry_L
[ -d "$d" ] && { printf '  step=%-7s 行=%-5s 快照=%s\n' \
  "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)" \
  "$(wc -l < "$d/series.csv" 2>/dev/null)" \
  "$(ls "$d" | grep -c '^snap_')"; tail -2 "$d/series.csv" | cut -d, -f1,9,10,19,24; }
