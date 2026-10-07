#!/usr/bin/env bash
# _r387_status.sh -- 裁定记录后的收尾核对 + goodA 进度
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
printf 'ledger 行数      : %s\n' "$(wc -l < R30_AUDIT_LEDGER.md)"
printf 'ledger 制表符行  : %s\n' "$(grep -c -P '\t' R30_AUDIT_LEDGER.md || true)"
printf 'summary 行数     : %s\n' "$(wc -l < AUDIT_SUMMARY_R76.md)"
printf 'summary 制表符行 : %s\n' "$(grep -c -P '\t' AUDIT_SUMMARY_R76.md || true)"
echo
echo "=== 裁定记录是否就位 ==="
grep -c '已裁定（用户，2026-10-01' R30_AUDIT_LEDGER.md
grep -c '§182' R30_AUDIT_LEDGER.md
echo
echo "=== goodA_400 进度 ==="
f=_w2_r386_run.log
if [ -f "$f" ]; then
  grep -oE '^  \[ *[0-9]*\]' "$f" | tail -2
  grep -oE '[0-9.]+s/步' "$f" | tail -1
  ls _exp/_bk_mb/dry_goodA_400/snap_*.npz 2>/dev/null | tail -1
else
  echo "  (还没开始写日志)"
fi
echo "_bk_exp 进程数: $(pgrep -c -f '_bk_exp[.]py' || echo 0)"
free -g | head -2
