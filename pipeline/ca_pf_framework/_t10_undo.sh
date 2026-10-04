#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _seed_undo_* 的定义位置 ==="
grep -n "_seed_undo_note\|_seed_undo_apply\|undo=" windowB_surface.py | cut -c1-165
echo
echo "=== seed_plate 签名与 undo 记账点 ==="
grep -n "def seed_plate" windowB_surface.py
L=$(grep -n "def seed_plate" windowB_surface.py | head -1 | cut -d: -f1)
awk -v s=$L -v e=$((L+70)) 'NR>=s && NR<=e{printf "%5d|%s\n", NR, $0}' windowB_surface.py | grep -nE "undo|bak|phi\[|max\(|-sdf|append|return" | head -30 | cut -c1-165
