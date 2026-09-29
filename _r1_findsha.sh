#!/bin/bash
# ★ 找出 lath1/mid1 用的那个引擎版本（SHA a3e355722b7e4914）并 diff 到当前
cd /mnt/f/speed_up || exit 1
F=pipeline/ca_pf_framework/windowB_surface.py
echo "=== 当前 SHA ==="
sha256sum "$F" | cut -c1-16
echo
echo "=== 最近 20 个改过该文件的提交，各自的 SHA ==="
for c in $(git log --format=%h -20 -- "$F"); do
  s=$(git show "$c:$F" 2>/dev/null | sha256sum | cut -c1-16)
  d=$(git log -1 --format='%ad %s' --date=format:'%H:%M' "$c" | cut -c1-70)
  echo "  $c  $s  $d"
done
