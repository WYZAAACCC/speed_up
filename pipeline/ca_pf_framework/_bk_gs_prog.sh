#!/usr/bin/env bash
# _bk_gs_prog.sh —— gs 根下各臂的进度一览
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "--- 臂 / 最后一行 series.csv"
for D in _exp/_bk_gs/dry_* _exp/_bk_block/dry_nr _exp/_bk_block/dry_p3; do
  [ -d "$D" ] || continue
  L=$(tail -1 "$D/series.csv" 2>/dev/null | cut -c1-165)
  printf '%-30s %s\n' "$(basename "$D")" "${L:-（无 series.csv）}"
done
echo "--- 负载/内存"
uptime
free -g | sed -n 2p
