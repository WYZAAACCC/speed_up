#!/bin/bash
# _r207_state.sh —— 开工前核对当前状态（不假设上一轮叙述仍成立）。
cd "$(dirname "$0")" || exit 1
echo "=== 文档行数 ==="
printf '  ledger  = %s\n' "$(wc -l < R30_AUDIT_LEDGER.md)"
printf '  summary = %s\n' "$(wc -l < AUDIT_SUMMARY_R76.md)"
echo
echo "=== 台账最后一节 ==="
grep -n '^## §' R30_AUDIT_LEDGER.md | tail -3
echo
echo "=== 残留进程 ==="
n=$(pgrep -fc '_bk_exp[.]py' || true)
echo "  _bk_exp.py 进程数 = ${n:-0}"
echo
echo "=== 内存 ==="
free -m | head -2
echo
echo "=== 关键代码行是否还在（速度律三项）==="
grep -n 'dG_cell = ' windowB_surface.py
grep -n 'kap_cell' windowB_surface.py | head -5
echo
echo "=== _bk_exp.py 里 advance 的调用点 ==="
grep -n 'g.advance(' _bk_exp.py
