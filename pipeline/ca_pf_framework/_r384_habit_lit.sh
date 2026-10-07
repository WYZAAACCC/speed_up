#!/usr/bin/env bash
# _r384_habit_lit.sh -- 项目文档里用的实验惯习面值是什么
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== 顶层 .md 里出现 334 / 344 / 225 的 ==="
for f in *.md; do
  n=$(grep -cE '\{?334\}?|\{?344\}?|\{?225\}?' "$f" 2>/dev/null || true)
  [ "${n:-0}" -gt 0 ] 2>/dev/null && printf '  %-44s %s 处\n' "$f" "$n"
done
echo
echo "=== 具体上下文（前 12 条）==="
for f in *.md; do
  grep -nE '\{?334\}?|\{?344\}?|\{?225\}?' "$f" 2>/dev/null | head -3 | sed "s|^|  [$f] |"
done | head -14
echo
echo "=== NPF 的来历（生成器/文档）==="
grep -n 'NPF' windowB_ti64_variants.py | head -8
