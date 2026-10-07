#!/usr/bin/env bash
# _r382_find_lit.sh -- 只看顶层文档，别递归扫 _exp（那里有几百个大文件，会超时）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== 顶层目录 ==="
ls -d */ 2>/dev/null | head -20
echo
echo "=== 顶层与 lit/ 相关的 .md ==="
ls *.md 2>/dev/null | grep -iE 'lit|anchor|habit|ref' | head -20
echo
echo "=== 含 '惯习面' 或 'habit plane' 的顶层 .md ==="
for f in *.md; do
  if grep -qiE '惯习面|habit plane' "$f" 2>/dev/null; then
    printf '  %-44s %s 处\n' "$f" "$(grep -ciE '惯习面|habit plane' "$f")"
  fi
done
echo
echo "=== 含 '{334}' 或 '334' 惯习面的顶层 .md ==="
for f in *.md; do
  if grep -qE '334|344|225' "$f" 2>/dev/null; then
    printf '  %-44s\n' "$f"
  fi
done
