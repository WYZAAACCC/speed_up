#!/usr/bin/env bash
# _r740_check.sh —— 查 T11 `G2` A/B 的**结果是否已存在**（`_t11_iface_ab.py` 的 OUT）。
set -uo pipefail
D=/mnt/f/speed_up/_exp/_bk_t5
echo "=== $D 存在? ==="
if [ -d "$D" ]; then
  echo "  是；条目数 = $(ls -1 "$D" | wc -l)"
  ls -1 "$D" | head -20 | sed 's/^/    /'
else
  echo "  ⛔ 不存在"
fi
echo
for t in ifaceOFF ifaceON; do
  echo "--- dry_$t ---"
  if [ -d "$D/dry_$t" ]; then
    ls -la --time-style='+%m-%d %H:%M' "$D/dry_$t" | tail -8 | sed 's/^/    /'
    if [ -f "$D/dry_$t/series.csv" ]; then
      echo "    series.csv 行数 = $(wc -l < "$D/dry_$t/series.csv")"
    fi
    if [ -f "$D/dry_$t/nuc_dbg.json" ]; then
      echo "    nuc_dbg.json 存在"
    fi
  else
    echo "    （无）"
  fi
done
echo
echo "=== 相关日志 ==="
ls -la --time-style='+%m-%d %H:%M' /mnt/f/speed_up/_w2_iface*.log 2>/dev/null | sed 's/^/  /' || echo "  （无）"
