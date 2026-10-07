#!/usr/bin/env bash
# R505 —— R503 四臂状态 + abA
set -u
cd "$(dirname "$0")"
printf 'abA: '
tail -1 _exp/_bk_mb/dry_abA/series.csv 2>/dev/null | cut -c1-30
echo
for T in r503B0 r503B1 r503B8 r503BIG; do
  L="_w2_r503_${T}.log"
  C="_exp/_bk_mb/dry_${T}/series.csv"
  NE=0; [ -f "$L" ] && NE=$(grep -c 'athermal 形核' "$L" || true)
  NC=0; [ -f "$C" ] && NC=$(wc -l < "$C")
  printf '  %-9s athermal事件=%-5s CSV行=%-5s\n' "$T" "$NE" "$NC"
done
echo
tail -3 _w2_r503_outer.log 2>/dev/null || echo "（outer 未写）"
echo "进程数: $(pgrep -c -f '_bk_exp' || echo 0)"
