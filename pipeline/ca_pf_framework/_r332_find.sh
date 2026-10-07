#!/usr/bin/env bash
# _r332_find.sh -- 找最近写入的臂目录
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb
echo "=== newest 25 dirs in _bk_mb ==="
ls -lat --time-style=+%m-%d_%H:%M "$D" | head -28
echo
echo "=== dirs matching tags ==="
ls -d "$D"/*saSet2P0* "$D"/*P0* "$D"/*200* 2>&1 | head -20
