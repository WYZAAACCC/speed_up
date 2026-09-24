#!/bin/bash
# Window B 夜班快照提交（只加源码/文档/图；重产物见 .gitignore）
cd /mnt/f/speed_up || exit 1
git reset -q
git add .gitignore AGENTS.md pipeline/RESEARCH_INTENT.md docs/agent-notes
git add pipeline/ca_pf_framework/*.py pipeline/ca_pf_framework/*.md \
        pipeline/ca_pf_framework/*.txt pipeline/ca_pf_framework/*.sh
git add bench/windowB_rve3d/*.png bench/windowB_rve3d/*.txt
git add bench/exaca bench/exaca_src
git add _*.py _*.sh
echo "== staged: $(git diff --cached --name-only | wc -l) files"
git diff --cached --numstat | awk '{a+=$1; b+=$2} END {print "lines +"a" -"b}'
git diff --cached --name-only | while read -r f; do
  [ -f "$f" ] && printf '%8s %s\n' "$(du -h "$f" | cut -f1)" "$f"
done | sort -rh | head -8
