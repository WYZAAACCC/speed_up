#!/bin/bash
# _r581_argminnorm.sh --- ★★★★★ 读 `argmin_normal`（记忆化优化的**最后一道前提**）
#   判据：若它**只依赖 `de`**（不依赖 k/l/场号）⇒ 记忆化**安全**；
#         若它还依赖 k/l 本身 ⇒ **不许记忆化**（会改结果）。
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_argminnorm.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① 定义点与调用点'
  grep -rn "def argmin_normal\|argmin_normal(" windowB_surface.py windowB_pf3d.py _bk_exp.py 2>/dev/null | head -12
  echo
  echo '## ② 定义体（从 def 起 70 行）'
  LN=$(grep -n "def argmin_normal" windowB_surface.py windowB_pf3d.py 2>/dev/null | head -1 | cut -d: -f2)
  F=$(grep -ln "def argmin_normal" windowB_surface.py windowB_pf3d.py 2>/dev/null | head -1)
  if [ -n "$LN" ] && [ -n "$F" ]; then
    echo "  在 $F:$LN"
    E=$((LN + 70))
    awk -v s="$LN" -v e="$E" 'NR>=s && NR<=e {printf "%5d| %s\n", NR, $0}' "$F"
  else
    echo "  ⚠ 没找到 def argmin_normal（可能在别的文件）"
    grep -rn "argmin_normal" *.py 2>/dev/null | head -10
  fi
} > "$OUT" 2>&1
cat "$OUT"
