#!/bin/bash
cd /mnt/f/speed_up || exit 1
rm -f .git/index.lock
rm -f pipeline/ca_pf_framework/_enc_test.txt p.i
git reset -q
git add .gitignore AGENTS.md pipeline/RESEARCH_INTENT.md
git add docs/agent-notes docs/LIT_SEARCH_HITS_Ti64.md docs/LIT_SEARCH_BRIEF_Ti64_THERMO.md \
        docs/LIT_SEARCH_BRIEF_Ti64_LPBF.md 2>/dev/null
git add pipeline/ca_pf_framework/*.py pipeline/ca_pf_framework/*.md \
        pipeline/ca_pf_framework/*.sh pipeline/ca_pf_framework/*.txt
git add pipeline/ca_pf_framework/pf1d_moose/*.py pipeline/ca_pf_framework/pf1d_moose/*.md \
        pipeline/ca_pf_framework/pf1d_moose/*.sh pipeline/ca_pf_framework/pf1d_moose/*.txt \
        pipeline/ca_pf_framework/pf1d_moose/*.i pipeline/ca_pf_framework/pf1d_moose/*.csv 2>/dev/null
echo "== staged: $(git diff --cached --name-only | wc -l) files"
git diff --cached --numstat | awk '{a+=$1; b+=$2} END {print "lines +"a" -"b}'
git diff --cached --name-only | while read -r f; do
  [ -f "$f" ] && printf '%8s %s\n' "$(du -h "$f" | cut -f1)" "$f"
done | sort -rh | head -10