#!/bin/bash
# _r291_step.sh —— 量 `_r280` 两臂的**真实步时**（判断 400 步是否可接受）。
cd "$(dirname "$0")" || exit 1
echo "=== 现在 $(date '+%T') ==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log \
         _w2_r253_L0.log _w2_r253_P0.log _w2_r225_p45L.log; do
  [ -f "$f" ] || { printf '  %-34s (无)\n' "$f"; continue; }
  st=$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')
  sz=$(stat -c %s "$f")
  tm=$(grep -o '[0-9.]*s/步' "$f" | tail -2 | tr '\n' ' ')
  printf '  %-34s 步=%-5s size=%-7s 最近步时=%s\n' "$f" "${st:-?}" "$sz" "$tm"
done
echo
echo "=== 两臂的 wall_s（series.csv 记录，比日志更权威）==="
for d in saSet2P0 saSet2F2P0 p45L0 p45P0; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  [ -f "$f" ] || { printf '  %-12s (无)\n' "$d"; continue; }
  tail -1 "$f" | awk -F, -v d="$d" '{printf "  %-12s step=%-5s wall_s=%-10s ⇒ %.2f s/步\n", d, $1, $3, ($1>0?$3/$1:0)}'
done
