#!/bin/bash
# _r581_covcode.sh --- ★★★★★ 查 `cov`（F3 覆盖率拒绝）的**判据**：它在哪里累加、条件是什么
#   ⚠ 写成脚本再跑（嵌套引号在 PowerShell→WSL 里会被拆坏）
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_covcode.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① `cov` 计数器在哪里累加（主副本 3 个文件）'
  for f in windowB_surface.py _bk_exp.py windowB_pf3d.py; do
    echo "--- $f ---"
    grep -n "cov" "$f" 2>/dev/null | grep -vE "^\s*#" | head -25 || echo "  （无匹配）"
  done
  echo
  echo '## ② `_nuc['"'"'dbg'"'"']` 里 cov 的写点（含上下文）'
  grep -n "dbg\['cov'\]\|dbg\[\"cov\"\]\|'cov'\]\s*+=\|\"cov\"\]\s*+=" \
      windowB_surface.py _bk_exp.py 2>/dev/null | head -10 || echo "  （无直接写点）"
  echo
  echo '## ③ 找 "coverage" / "cover" 的判据（可能叫别的名）'
  grep -n "cover" windowB_surface.py 2>/dev/null | head -30 || echo "  （无匹配）"
} > "$OUT" 2>&1
cat "$OUT"
