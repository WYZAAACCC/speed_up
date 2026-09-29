#!/bin/bash
# R30-AUDIT：5 个代表算例的落盘物逐条清点（只读）
cd /mnt/f/speed_up/pipeline/ca_pf_framework/_exp || exit 1
for D in _bk_closed/dry_cl1b _bk_eng/eng_eng12 _bk_time/dry_nc3 e7_selfac _bk_block/dry_p3; do
  echo "##### $D"
  ls -la --time-style=+%m-%d_%H:%M "$D" | tail -n +4 | \
    awk '{printf "   %-32s %12s B  %s\n", $NF, $5, $6}'
  echo "     snap 步号: $(ls "$D"/snap_*.npz 2>/dev/null | sed 's/.*snap_//;s/\.npz//' | tr '\n' ' ')"
  echo "     du: $(du -sh "$D" | cut -f1)"
done
