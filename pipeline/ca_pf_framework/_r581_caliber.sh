#!/bin/bash
# _r581_caliber.sh --- 查 C5「220–450 根」这个**口径**是怎么来的（R105 登记）
#   ⚠ 写成脚本再跑（嵌套引号在 PowerShell→WSL 里会被拆坏）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_caliber.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① 在 R581 系列文档里搜 "220" 与 "450"（C5 口径的出处）'
  grep -n "220" R581_*.md 2>/dev/null | grep -iE "根|450|口径|C5" | head -20
  echo
  grep -n "450" R581_*.md 2>/dev/null | grep -iE "根|220|口径|C5" | head -20
  echo
  echo '## ② 搜 "B_max"（A11 的式子）出现在哪些地方'
  grep -rn "B_max" R581_*.md 2>/dev/null | head -15
  echo
  echo '## ③ 搜 "625" 与 "781"（R30 提到的另一口径）'
  grep -n "625\|781" R581_*.md 2>/dev/null | head -12
  echo
  echo '## ④ R502_BLOCKCOUNT.md 里的块数口径（如果文件在）'
  for f in R502_BLOCKCOUNT.md R507_SHAPE_CLOSURE.md R525_TASK5_PARAM_FINDINGS.md; do
    if [ -f "$f" ]; then
      echo "--- $f ---"
      grep -n "220\|450\|B_max\|块数" "$f" 2>/dev/null | head -10
    fi
  done
} > "$OUT" 2>&1
cat "$OUT"
