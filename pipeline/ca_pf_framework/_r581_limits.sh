#!/bin/bash
# _r581_limits.sh --- ★★★★★ 读框架 `limitations()` 的**第 1 条原文**（R130 登记的最高优先级）
#   为什么：引擎逐字说「**块的数目是输入、不是涌现** —— 框架 `limitations()` 第 1 条明写…」
#   ⇒ 这直接冲击 (5) 判据 ⑥（"涌现出自协调（自发，不是人为规定）"）⇒ **必须读原文**
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_limits.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① `limitations` 的定义点与调用点'
  grep -rn "def limitations\|limitations(" *.py 2>/dev/null | head -12
  echo
  echo '## ② 定义体（从 def 起 60 行）'
  F=$(grep -rln "def limitations" *.py 2>/dev/null | head -1)
  if [ -n "$F" ]; then
    LN=$(grep -n "def limitations" "$F" | head -1 | cut -d: -f1)
    echo "  在 $F:$LN"
    E=$((LN + 60))
    awk -v s="$LN" -v e="$E" 'NR>=s && NR<=e {printf "%5d| %s\n", NR, $0}' "$F"
  else
    echo "  ⚠ 没找到 def limitations ⇒ 换关键词"
    grep -rn "LIMITATIONS\|limitation" *.py 2>/dev/null | head -12
  fi
  echo
  echo '## ③ 谁**打印**了这句话（"块的数目是输入"）'
  grep -rn "块的数目是输入\|不是涌现" *.py 2>/dev/null | head -6 | cut -c1-130
} > "$OUT" 2>&1
cat "$OUT"
