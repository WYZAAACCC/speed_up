#!/usr/bin/env bash
# R471 —— 交付物收尾自检
set -u
cd "$(dirname "$0")"
echo "=== 1. 制表符检查（本仓库台账纪律：必须全 0）==="
for f in R2_PARAM_VERDICTS.md PHYSICS_FIRST_SPEC.md NEXT_TASKS_FOR_REVIEW.md; do
  if [ -f "$f" ]; then
    t=$(grep -cP '\t' "$f"); l=$(wc -l < "$f")
    printf '  %-30s tabs=%s  lines=%s\n' "$f" "$t" "$l"
  fi
done

echo
echo "=== 2. 关键数字是否落在文档里 ==="
for n in "641.7" "2.087e8" "0.1705" "0.0285" "1.234" "1.7412e7" "p=1.425" "frac_pos" "0.963"; do
  a=$(grep -cF -- "$n" R2_PARAM_VERDICTS.md 2>/dev/null); a=${a:-0}
  b=$(grep -cF -- "$n" PHYSICS_FIRST_SPEC.md 2>/dev/null); b=${b:-0}
  a=$(printf '%s' "$a" | head -1); b=$(printf '%s' "$b" | head -1)
  tot=$((a + b))
  if [ "$tot" -gt 0 ]; then s=OK; else s="❌ 两处都没有"; fi
  printf '  %-12s R2=%s SPEC=%s  %s\n' "$n" "$a" "$b" "$s"
done

echo
echo "=== 3. 本轮新增脚本 ==="
ls -1 _r46*.py _r47*.py _r464_reinitctl.sh _r471_finalcheck.sh 2>/dev/null

echo
echo "=== 4. 还在跑的仿真 ==="
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep -E '_bk_exp' | grep -v grep | cut -c1-95

echo
echo "=== 5. abA 进度 ==="
if [ -f _exp/_bk_mb/dry_abA/series.csv ]; then
  tail -1 _exp/_bk_mb/dry_abA/series.csv | awk -F, '{printf "  step=%s  t_s=%.6e  nreg_used=%s\n",$1,$2,$8}'
fi

echo
echo "=== 6. 资源 ==="
free -g | head -2
uptime
