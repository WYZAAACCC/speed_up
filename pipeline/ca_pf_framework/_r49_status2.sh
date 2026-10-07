#!/bin/bash
# R49: 用 series.csv 行数作为权威进度（run.log 名字不固定）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for root in _exp/_bk_mb _exp/_bk_closed; do
  echo "=== $root ==="
  for d in "$root"/*/; do
    b=$(basename "$d")
    [ -f "$d/series.csv" ] || continue
    n=$(wc -l < "$d/series.csv")
    ns=$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)
    nphi=$(ls "$d"/phi_*.npz 2>/dev/null | wc -l)
    mt=$(stat -c '%y' "$d/series.csv" | cut -c1-19)
    printf '%-12s rows=%-6s snap=%-4s phi=%-4s mtime=%s\n' "$b" "$n" "$ns" "$nphi" "$mt"
  done
done
echo "=== logs (framework dir, _w2_*) ==="
ls -t _w2_*_run.log 2>/dev/null | while read -r f; do
  printf '%-34s %8s lines  mtime=%s\n' "$f" "$(wc -l < "$f")" "$(stat -c '%y' "$f" | cut -c1-19)"
done
echo "=== tail of active logs ==="
for f in _w2_r47_dx62_run.log; do
  [ -f "$f" ] && { echo "--- $f"; tail -3 "$f"; }
done
echo "=== newest log overall ==="
newest=$(ls -t _w*_run.log 2>/dev/null | head -1); echo "$newest"; tail -4 "$newest"
