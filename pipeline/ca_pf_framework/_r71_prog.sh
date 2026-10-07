#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== R71 进度'
tail -5 _w2_r71_run.log 2>/dev/null
echo
for t in m3fp10 m3fp0; do
  d="_exp/_bk_mb/dry_$t"
  if [ -f "$d/series.csv" ]; then
    printf '  %-8s step=%-6s snap=%s\n' "$t" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-8s （无产物）\n' "$t"
  fi
done
