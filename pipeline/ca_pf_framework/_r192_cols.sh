#!/bin/bash
# _r192_cols.sh —— 列出 series.csv 的列名，并标出 `_r171` 判决脚本用到的那几列**在不在**。
cd "$(dirname "$0")" || exit 1
F=_exp/_bk_mb/dry_saSet2F2/series.csv
echo "=== 全部列名（%d 个）==="
head -1 "$F" | tr ',' '\n' | nl | tr '\n' ' '
echo
echo
echo "=== _r171_f2verdict.py 用到的列是否存在 ==="
for c in step r_selfac E_el_J Vt f3_area_m2 f2_area_m2 nf2 box_touch_core; do
  if head -1 "$F" | tr ',' '\n' | grep -qx "$c"; then
    echo "  $c  ✅"
  else
    echo "  $c  ❌ **不存在** —— 判决脚本会静默拿到 NaN！"
  fi
done
echo
echo "=== _r171 还用到（判据 G-3）==="
for c in blk_nprof nblk_sig; do
  if head -1 "$F" | tr ',' '\n' | grep -qx "$c"; then echo "  $c  ✅"; else echo "  $c  ❌ 不存在"; fi
done
