#!/bin/bash
# _r581_limits2.sh --- ★★★★★★ 读 `windowB_closure.py` 的 `limitations()` **完整定义**（A37 的直接依据）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_limits2.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  F=windowB_closure.py
  if [ ! -f "$F" ]; then
    echo "⚠ $F 不存在 ⇒ 找它"
    ls windowB_closure*.py 2>/dev/null
    grep -rln "def limitations" *.py 2>/dev/null
  fi
  echo "## 定义点"
  grep -n "def limitations" "$F" 2>/dev/null
  echo
  LN=$(grep -n "def limitations" "$F" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$LN" ]; then
    NXT=$(awk -v s="$LN" 'NR>s && /^def |^class /{print NR; exit}' "$F")
    [ -z "$NXT" ] && NXT=$((LN + 120))
    echo "## 定义体（$LN 到 $((NXT-1))，共 $((NXT-LN)) 行）"
    awk -v s="$LN" -v e="$((NXT-1))" 'NR>=s && NR<=e {printf "%5d| %s\n", NR, $0}' "$F"
    echo
    echo "## 条数统计"
    printf '  以四空格+引号开头的行（条数）= %s\n' \
      "$(awk -v s="$LN" -v e="$((NXT-1))" 'NR>=s && NR<=e && /^    .\x27/ {n++} END{print n+0}' "$F")"
  fi
} > "$OUT" 2>&1
cat "$OUT"
