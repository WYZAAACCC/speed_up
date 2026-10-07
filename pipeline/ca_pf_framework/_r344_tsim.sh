#!/usr/bin/env bash
# _r344_tsim.sh -- 用 series.csv 的物理时间直接判定 reinit 触发条件
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb
for n in dry_saSet2 dry_saSet2P0 dry_saSet2F2P0 dry_near200; do
  f="$D/$n/series.csv"
  [ -f "$f" ] || { echo "$n: 无 series.csv"; continue; }
  hdr=$(head -1 "$f")
  # 找 t_s 列号
  col=$(printf '%s' "$hdr" | tr ',' '\n' | grep -n '^t_s$' | cut -d: -f1)
  last=$(tail -1 "$f")
  ts=$(printf '%s' "$last" | cut -d, -f"$col")
  echo "$n: 列号=$col  末 t_s=$ts"
  echo "   reinit_dt=1e-4 ⇒ 需要 t_s 累积到 1e-4；比值 = $(awk -v a="$ts" 'BEGIN{printf "%.4f", a/1e-4}')"
done
echo
echo "=== meta.json 里的 reinit 相关键 ==="
for n in dry_saSet2P0; do
  grep -o '"reinit[^,]*' "$D/$n/meta.json" 2>/dev/null | head -10
done
