#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 带宽扫描进度'
tail -8 _w2_r56_band_run.log 2>/dev/null
echo
for t in bc5 bc10 bc20 bc40; do
  d="_exp/_bk_mb/dry_$t"
  if [ -f "$d/series.csv" ]; then
    printf '  %-6s step=%-6s snap=%s\n' "$t" \
      "$(tail -1 "$d/series.csv" | cut -d, -f1)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-6s （无产物）\n' "$t"
  fi
done
