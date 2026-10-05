#!/bin/bash
cd /mnt/f/speed_up || exit 1
echo "=== ① 未跟踪文件里，属于本会话产出的（_t10_* / R59* / R60* / _t5_patch_* / _w2_t10_*）==="
git ls-files --others --exclude-standard \
  | grep -E '(^|/)(_t10_|R59[0-9]|R60[0-9]|_t5_patch_|_w2_t10_)' | head -60
echo -n "  条数 = "
git ls-files --others --exclude-standard \
  | grep -cE '(^|/)(_t10_|R59[0-9]|R60[0-9]|_t5_patch_|_w2_t10_)'
echo
echo "=== ② 未跟踪文件按顶层目录归类（前 20）==="
git ls-files --others --exclude-standard | awk -F/ '{print $1}' | sort | uniq -c | sort -rn | head -20
echo
echo "=== ③ 未跟踪文件按扩展名归类（前 15）==="
git ls-files --others --exclude-standard | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15
echo
echo "=== ④ 未跟踪文件总体积 ==="
git ls-files --others --exclude-standard -z | du -ch --files0-from=- 2>/dev/null | tail -1
echo
echo "=== ⑤ .gitignore 现状 ==="
if [ -f .gitignore ]; then wc -l .gitignore; head -30 .gitignore; else echo "  （无 .gitignore）"; fi
