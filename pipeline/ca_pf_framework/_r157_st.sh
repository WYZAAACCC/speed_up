#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)"
free -g | sed -n '2p'
echo
for t in saSet2E0 saOddGE0; do
  printf -- '  %-10s %s\n' "$t" "$(grep 's/步' _w2_r155_${t}.log 2>/dev/null | tail -1 | cut -c1-95)"
done
echo
echo "--- 台账规模 ---"
wc -l R30_AUDIT_LEDGER.md
grep -c '^## §' R30_AUDIT_LEDGER.md
