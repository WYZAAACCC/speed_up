#!/bin/bash
# _r581_ledchk.sh --- 复核账本更新：4 条过时状态是否已改、还剩几条"未动"
cd "$(dirname "$0")" || exit 1
F=OPOPT_LEDGER.md
echo "NOW = $(date '+%F %T')"
echo
echo '── 文件行数 ──'
wc -l < "$F" | sed 's/^/  /'
echo
echo '── 4 条目标行的**状态列**（第 4 个字段）──'
for n in 22 30 32 36; do
  line=$(sed -n "${n}p" "$F")
  tag=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')
  st=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$5); print $5}')
  printf '  %-6s %s\n' "$tag" "$(printf '%s' "$st" | cut -c1-72)"
done
echo
echo '── 全表还有多少条写着「未动」/「未做」──'
grep -c '未动' "$F" | sed 's/^/  含"未动"的行数=/'
grep -c '未做' "$F" | sed 's/^/  含"未做"的行数=/'
echo
echo '── 这些"未动"具体是哪几条 ──'
grep -n '未动' "$F" | cut -c1-118 | sed 's/^/  /'
echo
echo '── 表前缀计数（P36 的判据：应等于条目数）──'
grep -cE '^\| \*?\*?[A-Z][0-9]+' "$F" | sed 's/^/  条目行数=/'
