#!/usr/bin/env bash
# _r351_lint.sh -- ledger 卫生 + 新工具语法自检
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "ledger 行数: $(wc -l < R30_AUDIT_LEDGER.md)"
echo "含制表符的行数: $(grep -c -P '\t' R30_AUDIT_LEDGER.md || true)"
echo "已就地指针（'§' 更正/更正指针 行数）: $(grep -c -E '更正（§|⚠ 更正|就地加更正指针' R30_AUDIT_LEDGER.md || true)"
echo
echo "=== 新工具语法自检 ==="
for f in _r334_c1diag.py _r335_overlap.py _r336_graderr.py _r338_sdfgrad.py \
         _r339_medial.py _r341_truedist.py _r348_dtjson.py _r349_f2geom.py \
         _r350_f2inert.py _r295_r280verdict.py; do
  if /root/miniconda3/envs/ml/bin/python -m py_compile "$f" 2>/tmp/_pe; then
    echo "  ok   $f"
  else
    echo "  FAIL $f"; head -3 /tmp/_pe
  fi
done
echo
echo "=== ledger 末尾 ==="
tail -3 R30_AUDIT_LEDGER.md
