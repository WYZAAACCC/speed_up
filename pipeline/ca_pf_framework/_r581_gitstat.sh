#!/bin/bash
# _r581_gitstat.sh --- 查清 git 仓库状态（决定"怎么提交才安全"）
cd /mnt/f/speed_up || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 仓库根、分支、HEAD ════'
echo "  git rev-parse --show-toplevel : $(git rev-parse --show-toplevel 2>&1)"
echo "  分支                          : $(git branch --show-current 2>&1)"
echo "  HEAD                          : $(git log --oneline -1 2>&1)"
echo "  提交总数                      : $(git rev-list --count HEAD 2>&1)"
echo
echo '════ ② 改动规模 ════'
echo "  已跟踪·被改 : $(git diff --name-only 2>/dev/null | wc -l)"
echo "  已跟踪·被删 : $(git diff --diff-filter=D --name-only 2>/dev/null | wc -l)"
echo "  已暂存      : $(git diff --cached --name-only 2>/dev/null | wc -l)"
echo "  未跟踪文件  : $(git ls-files --others --exclude-standard 2>/dev/null | wc -l)"
echo
echo '════ ③ .gitignore ════'
if [ -f .gitignore ]; then
  echo "  存在，共 $(wc -l < .gitignore) 行；前 25 行："
  head -25 .gitignore | sed 's/^/    /'
else
  echo '  **不存在**'
fi
echo
echo '════ ④ ★ 未跟踪文件的体积（决定能不能 git add -A）════'
echo '  按目录聚合（前 15，按体积降序）：'
git ls-files --others --exclude-standard 2>/dev/null \
  | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -15 | sed 's/^/    /'
echo
echo '  未跟踪文件的**总体积**（前 2000 个，可能不全）：'
git ls-files --others --exclude-standard 2>/dev/null | head -2000 \
  | while read -r f; do [ -f "$f" ] && stat -c%s "$f"; done \
  | awk '{s+=$1} END {printf "    %.2f GB（%d 个文件）\n", s/1073741824, NR}'
echo
echo '════ ⑤ 已跟踪文件里最大的 10 个（判断仓库本身是否已经很大）════'
git ls-files 2>/dev/null | while read -r f; do [ -f "$f" ] && stat -c%s "$f"; done 2>/dev/null \
  | sort -rn | head -10 | awk '{printf "    %.2f MB\n", $1/1048576}'
echo
echo '════ ⑥ .git 目录体积 ════'
du -sh .git 2>/dev/null | sed 's/^/  /'
