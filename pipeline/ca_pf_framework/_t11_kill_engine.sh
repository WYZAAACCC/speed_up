#!/bin/bash
# _t11_kill_engine.sh —— 只杀 `_bk_exp.py`，**不用 `pkill -f`**（那会杀掉自己的 shell，
#   见 AGENTS.md §3.10）。做法：按 `pgrep -x python` 拿到 PID，再逐个查 `/proc/<pid>/cmdline`。
set -u
PY_NAMES="python python3"
FOUND=0
for N in $PY_NAMES; do
  for X in $(pgrep -x "$N" 2>/dev/null); do
    if tr '\0' ' ' < "/proc/$X/cmdline" 2>/dev/null | grep -q '_bk_exp.py'; then
      echo "  → 杀 _bk_exp.py  PID=$X"
      kill -9 "$X" 2>/dev/null
      FOUND=1
    fi
  done
done
[ "$FOUND" -eq 0 ] && echo "  （没有找到 _bk_exp.py 进程）"
sleep 2
echo "--- 复查 ---"
if pgrep -af _bk_exp.py > /tmp/_chk.txt 2>/dev/null; then
  echo "  ❌ **仍有残留**："; cat /tmp/_chk.txt
else
  echo "  ✅ 已无 _bk_exp.py 进程"
fi
