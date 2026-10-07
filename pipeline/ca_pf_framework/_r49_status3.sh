#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for d in _exp/_bk_mb/dry_mb1L _exp/_bk_mb/dry_mb1Ls _exp/_bk_mb/dry_mb1s62 _exp/_bk_closed/dry_cln11; do
  echo "=== $d"
  ls -la "$d" | head -14
  echo "--- header + last row of series.csv"
  head -1 "$d/series.csv" | cut -c1-160
  tail -1 "$d/series.csv" | cut -c1-160
done
