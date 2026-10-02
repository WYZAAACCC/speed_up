#!/bin/bash
# _r581_paircode.sh --- 读 `_pair_normals` 的实现（goal §(14) 要求"评估优化，不许绕过"）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_paircode.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① 定义点'
  grep -n "_pair_normals" windowB_surface.py 2>/dev/null
  echo
  echo '## ② 定义体（从 def 起 55 行）'
  LN=$(grep -n "def _pair_normals" windowB_surface.py | head -1 | cut -d: -f1)
  if [ -n "$LN" ]; then
    E=$((LN + 55))
    awk -v s="$LN" -v e="$E" 'NR>=s && NR<=e {printf "%5d| %s\n", NR, $0}' windowB_surface.py
  else
    echo "  ⚠ 没找到 def _pair_normals"
  fi
  echo
  echo '## ③ 其它构造期的大块（找构造期里可能的 O(nv²) 或 O(nv·N³)）'
  grep -n "def __init__\|def _build\|def _setup\|np.zeros(\|np.empty(" windowB_surface.py 2>/dev/null | head -25
} > "$OUT" 2>&1
cat "$OUT"
