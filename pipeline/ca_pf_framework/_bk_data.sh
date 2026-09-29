#!/bin/bash
# _bk_data.sh —— 检查"全过程数据落盘 F 盘"（用户明确要求）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _exp/_bk_block/ ==="
ls -1 _exp/_bk_block/ 2>/dev/null
for d in _exp/_bk_block/*_p2; do
  [ -d "$d" ] || continue
  echo "--- $d ---"
  ls -la "$d" | head -8
  echo -n "  总大小: "; du -sh "$d" | cut -f1
  echo -n "  series.csv 行数: "; wc -l < "$d/series.csv" 2>/dev/null || echo "无"
done
echo "=== F 盘余量 ==="
df -h /mnt/f | tail -1
