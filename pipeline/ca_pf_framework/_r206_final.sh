#!/bin/bash
# _r206_final.sh —— 收尾核对：行数、新节、制表符、关键产物是否都在。
cd "$(dirname "$0")" || exit 1
echo "=== 文档 ==="
printf '  %-28s %s 行\n' R30_AUDIT_LEDGER.md "$(wc -l < R30_AUDIT_LEDGER.md)"
printf '  %-28s %s 行\n' AUDIT_SUMMARY_R76.md "$(wc -l < AUDIT_SUMMARY_R76.md)"
echo
echo "=== 本轮新增的台账节 ==="
grep -n '^## §1[23][0-9]' R30_AUDIT_LEDGER.md | sed 's/^/  /'
echo
echo "=== 制表符计数（都应为 0）==="
for f in R30_AUDIT_LEDGER.md AUDIT_SUMMARY_R76.md; do
  printf '  %-28s %s\n' "$f" "$(tr -cd '\t' < "$f" | wc -c)"
done
echo
echo "=== 本轮关键脚本/日志是否在位 ==="
for f in _r172_omega_audit.py _r175_r165pre.py _r176_f2gamma_check.py \
         _r178_repro.py _r179_inert.sh _r182_omega_check.py _r184_inert_cmp.py \
         _r189_ncmp_from_region.py _r194_bandscan.py _r199_r165final.py \
         _r200_termbalance.py _w2_r182.log _w2_r184.log _w2_r199.log _w2_r200.log \
         _w2_r202_regress.log; do
  [ -f "$f" ] && printf '  ✅ %s\n' "$f" || printf '  ❌ %s （缺失）\n' "$f"
done
echo
echo "=== 进程残留（应为 0）==="
pgrep -fc '_bk_exp[.]py' || echo 0
