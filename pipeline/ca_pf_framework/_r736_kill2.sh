#!/usr/bin/env bash
# _r736_kill2.sh —— 停掉 launcher + 它起的子进程（`N=128` 内存不可行）。
set -uo pipefail
echo "=== 杀 launcher（_r733_longab.py）与其 shell ==="
for P in $(pgrep -f '_r733_longab.py'); do
  echo "  kill -9 $P  ($(ps -o args= -p $P | cut -c1-60))"
  kill -9 "$P" 2>/dev/null || true
done
sleep 2
echo "=== 杀 _bk_exp.py ==="
for P in $(pgrep -f '[_]bk_exp.py'); do
  echo "  kill -9 $P"
  kill -9 "$P" 2>/dev/null || true
done
sleep 3
echo
echo "=== 验证 ==="
for pat in '[_]bk_exp.py' '_r733_longab'; do
  if pgrep -af "$pat"; then echo "  ⛔ $pat 仍有存活"; else echo "  ✅ $pat 已清"; fi
done
free -m | head -2
