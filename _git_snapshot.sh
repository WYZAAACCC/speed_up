#!/bin/bash
# 快照: 统计 + 提交（排除大数组, 见 .gitignore）
cd /mnt/f/speed_up || exit 1
echo "== staged files: $(git diff --cached --name-only | wc -l)"
git diff --cached --numstat | awk '{a+=$1; b+=$2} END {print "lines +"a" -"b}'
echo "== staged size (top 10) =="
git diff --cached --name-only | while read -r f; do
  [ -f "$f" ] && printf '%8s %s\n' "$(du -h "$f" | cut -f1)" "$f"
done | sort -rh | head -10
