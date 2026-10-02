#!/bin/bash
# _r581_gitplan.sh --- 定"怎么提交才安全"：看清 29 个被改 + 哪些新文件能进 git
cd /mnt/f/speed_up || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 已跟踪·被改的 29 个（含体积与类型）════'
git diff --name-only 2>/dev/null | while read -r f; do
  [ -f "$f" ] || { printf '  %-70s （已删/不在）\n' "$f"; continue; }
  printf '  %-70s %8.1f KB\n' "$f" "$(stat -c%s "$f" | awk '{print $1/1024}')"
done
echo
echo '════ ② 被改文件里最大的 5 个（防有大数据混进来）════'
git diff --name-only 2>/dev/null | while read -r f; do
  [ -f "$f" ] && stat -c'%s %n' "$f"
done | sort -rn | head -5 | awk '{printf "  %8.2f MB  %s\n", $1/1048576, $2}'
echo
echo '════ ③ ★ 未跟踪文件按**类型**统计（决定收哪些）════'
git ls-files --others --exclude-standard 2>/dev/null \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -14 | sed 's/^/  /'
echo
echo '════ ④ ★ 未跟踪文件里，**>1 MB** 的有多少个、共多大（这些一律不进 git）════'
git ls-files --others --exclude-standard 2>/dev/null | head -4000 | while read -r f; do
  [ -f "$f" ] || continue
  s=$(stat -c%s "$f")
  [ "$s" -gt 1048576 ] && printf '%s %s\n' "$s" "$f"
done > /tmp/_big.txt 2>/dev/null
printf '  >1MB 的文件数：%s；合计 %.2f GB\n' \
  "$(wc -l < /tmp/_big.txt)" \
  "$(awk '{s+=$1} END {printf "%.2f", s/1073741824}' /tmp/_big.txt)"
echo '  最大的 8 个：'
sort -rn /tmp/_big.txt | head -8 | awk '{printf "    %8.1f MB  %s\n", $1/1048576, $2}'
echo
echo '════ ⑤ ★ 候选：`pipeline/ca_pf_framework/` 下**未跟踪的文本小文件** ════'
git ls-files --others --exclude-standard pipeline/ca_pf_framework 2>/dev/null \
  | grep -E '\.(py|sh|md|txt|tsv)$' \
  | while read -r f; do
      [ -f "$f" ] || continue
      s=$(stat -c%s "$f")
      [ "$s" -lt 524288 ] && printf '%s %s\n' "$s" "$f"
    done | sort -rn > /tmp/_cand.txt 2>/dev/null
printf '  候选数：%s；合计 %.2f MB\n' \
  "$(wc -l < /tmp/_cand.txt)" \
  "$(awk '{s+=$1} END {printf "%.2f", s/1048576}' /tmp/_cand.txt)"
echo '  （前 12 个）'
head -12 /tmp/_cand.txt | awk '{printf "    %7.1f KB  %s\n", $1/1024, $2}'
