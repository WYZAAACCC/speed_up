#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== R75 进度'
tail -4 _w2_r75_run.log 2>/dev/null
for t in mb2fp10 mb2fp0; do
  d="_exp/_bk_mb/dry_$t"
  if [ -f "$d/series.csv" ]; then
    printf '  %-9s step=%-6s snap=%s\n' "$t" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-9s （无产物）\n' "$t"
  fi
done
