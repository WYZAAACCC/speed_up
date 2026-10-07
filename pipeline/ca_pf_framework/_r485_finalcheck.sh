#!/usr/bin/env bash
# R485 —— 本轮收尾自检
set -u
cd "$(dirname "$0")"
echo "=== 1. 制表符检查（必须全 0）==="
for f in R2_PARAM_VERDICTS.md PHYSICS_FIRST_SPEC.md R477_QS_CLOCK.md R479_SUPERCRIT.md R481_NUC_SITES.md; do
  if [ -f "$f" ]; then
    printf '  %-26s tabs=%s lines=%s\n' "$f" "$(grep -cP '\t' "$f")" "$(wc -l < "$f")"
  else
    printf '  %-26s **不存在**\n' "$f"
  fi
done

echo
echo "=== 2. 本轮关键数字 ==="
for n in "sites_refill" "sites_refilled" "8 / 8" "0.00%" "init_parent" "nuc-max-per-step" "fresh 被 stack 饿死"; do
  c=$(grep -rlF -- "$n" R2_PARAM_VERDICTS.md R481_NUC_SITES.md 2>/dev/null | tr '\n' ' ')
  if [ -n "$c" ]; then s="OK  ($c)"; else s="❌ 两处都没有"; fi
  printf '  %-18s %s\n' "$n" "$s"
done

echo
echo "=== 3. 在跑的仿真 ==="
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep -E '[_]bk_exp' | cut -c1-80

echo
echo "=== 4. abA 进度 ==="
if [ -f _exp/_bk_mb/dry_abA/series.csv ]; then
  tail -1 _exp/_bk_mb/dry_abA/series.csv | awk -F, '{printf "  step=%s  t_s=%.6e  Vt=%.4e  nreg=%s\n",$1,$2,$6,$8}'
fi

echo
echo "=== 5. 资源 ==="
free -g | head -2
uptime
