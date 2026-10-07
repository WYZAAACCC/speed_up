#!/usr/bin/env bash
# R480 —— 交付物收尾自检（含本轮新增的三份文档）
set -u
cd "$(dirname "$0")"
echo "=== 1. 制表符检查（必须全 0）==="
for f in R2_PARAM_VERDICTS.md PHYSICS_FIRST_SPEC.md R477_QS_CLOCK.md R479_SUPERCRIT.md NEXT_TASKS_FOR_REVIEW.md; do
  if [ -f "$f" ]; then
    printf '  %-26s tabs=%s lines=%s\n' "$f" "$(grep -cP '\t' "$f")" "$(wc -l < "$f")"
  else
    printf '  %-26s **不存在**\n' "$f"
  fi
done

echo
echo "=== 2. 本轮关键数字是否落在文档里 ==="
for n in "3.1818e8" "377.7" "0.2842" "9.8039e5" "1.104" "641.7" "1792" "32760"; do
  c=$(grep -rlF -- "$n" R2_PARAM_VERDICTS.md R479_SUPERCRIT.md R477_QS_CLOCK.md PHYSICS_FIRST_SPEC.md 2>/dev/null | tr '\n' ' ')
  if [ -n "$c" ]; then s="OK  ($c)"; else s="❌ 四处都没有"; fi
  printf '  %-12s %s\n' "$n" "$s"
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
echo "=== 5. 新增脚本/文档 ==="
ls -1 _r47*.py _r47*.md _r47*.sh 2>/dev/null

echo
echo "=== 6. 资源 ==="
free -g | head -2
uptime
