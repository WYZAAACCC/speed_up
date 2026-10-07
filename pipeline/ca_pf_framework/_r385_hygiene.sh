#!/usr/bin/env bash
# _r385_hygiene.sh -- 收尾卫生（避免 PowerShell 吞掉 $(...)）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
printf 'ledger 行数        : %s\n' "$(wc -l < R30_AUDIT_LEDGER.md)"
printf 'ledger 制表符行    : %s\n' "$(grep -c -P '\t' R30_AUDIT_LEDGER.md || true)"
printf 'summary 行数       : %s\n' "$(wc -l < AUDIT_SUMMARY_R76.md)"
printf 'summary 制表符行   : %s\n' "$(grep -c -P '\t' AUDIT_SUMMARY_R76.md || true)"
echo
echo "=== 新工具语法自检 ==="
for f in _r373_eps0_check.py _r376_selfac_def.py _r377_selfac_subset.py \
         _r379_lis_check.py _r383_habit_vs_exp.py _r357_selfac_geom.py \
         _r358_ed_offline.py _r363_c2p_stable.py; do
  /root/miniconda3/envs/ml/bin/python -m py_compile "$f" && echo "  ok   $f" || echo "  FAIL $f"
done
echo
echo "=== 回归判据 ==="
grep -E '差异字段数|共有列逐位一致|FAIL = |总判定' _w2_r380_regress.log | head -5
