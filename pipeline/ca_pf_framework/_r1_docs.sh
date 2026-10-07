#!/bin/bash
# _r1_docs.sh --- 交付文档清单 + 核对入口文档引用的文件是否都存在
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== R1 交付文档（按大小）==="
ls -la R1_*.md 2>/dev/null | awk '{printf "%-48s %8s B\n", $9, $5}' | sort
echo
echo "=== R1_STATE.md 里引用到的 R1_*.md 是否都存在 ==="
miss=0
for f in $(grep -oE 'R1_[A-Za-z0-9_]+\.md' R1_STATE.md | sort -u); do
  if [ -f "$f" ]; then echo "  OK    $f"; else echo "  缺！  $f"; miss=$((miss+1)); fi
done
echo "  ---- 缺失 $miss 个 ----"
echo
echo "=== 关键脚本是否都在 ==="
for f in _r1_exp.py _r1_analyze.py _r1_aniso.py _r1_dxcurve.py _r1_dxconsist.py \
         _r1_armhealth.py _r1_selfac.py _r1_selfac2.py _r1_facetjudge.py \
         _r1_a3meta.py _r1_b1fix.py _r1_wtratio.py _r1_wtratio2.py _r1_bkchk.py; do
  [ -f "$f" ] && echo "  OK    $f" || echo "  缺！  $f"
done
