#!/bin/bash
# _r581_safemask.sh --- 复核 R32 的断言「`_nuc_safe_mask()` 是全仓零调用的死代码」（P28）
#   ⚠ 写成脚本再跑（嵌套引号在 PowerShell→WSL 里会被拆坏）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_safemask.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① 定义点（主副本 3 个文件，逐行）'
  for f in _bk_exp.py windowB_surface.py windowB_pf3d.py; do
    echo "--- $f ---"
    grep -n "safe_mask" "$f" 2>/dev/null || echo "  （无匹配）"
  done
  echo
  echo '## ② 整个 ca_pf_framework 下的 .py（排除备份目录）'
  grep -rn --include='*.py' "safe_mask" . 2>/dev/null \
    | grep -v '_r580_backup/' | grep -v '_superseded' | head -30 \
    || echo "  （无匹配）"
  echo
  echo '## ③ 定义点上下文（若存在，打印 ±12 行）'
  LN=$(grep -n "def _nuc_safe_mask" windowB_surface.py 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$LN" ]; then
    S=$((LN - 12)); [ "$S" -lt 1 ] && S=1
    E=$((LN + 20))
    echo "  定义在 windowB_surface.py:$LN ⇒ 打印 $S..$E 行"
    sed -n "${S},${E}p" windowB_surface.py | cat -n
  else
    echo "  ⚠ windowB_surface.py 里没有 'def _nuc_safe_mask'"
  fi
} > "$OUT" 2>&1
cat "$OUT"
