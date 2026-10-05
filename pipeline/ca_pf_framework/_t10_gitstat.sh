#!/bin/bash
cd /mnt/f/speed_up || exit 1
echo "=== git status（简） ==="
git status --short | head -60
echo
echo "=== 未跟踪/修改统计 ==="
echo -n "  已跟踪但改动 = "; git diff --name-only | wc -l
echo -n "  已暂存        = "; git diff --cached --name-only | wc -l
echo -n "  未跟踪        = "; git ls-files --others --exclude-standard | wc -l
echo
echo "=== 未跟踪文件清单（前 40）==="
git ls-files --others --exclude-standard | head -40
echo
echo "=== 最近 5 次提交 ==="
git log --oneline -5
