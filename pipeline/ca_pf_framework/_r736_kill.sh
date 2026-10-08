#!/usr/bin/env bash
# _r736_kill.sh —— 安全中止长 A/B（`N=128` 内存失控：4 个场就 11.9 GB）。
# 纪律：按**精确进程名/PID** 杀，不用 `pkill -f`（`AGENTS.md §3.10`：会杀掉自己）；
#       杀完**必须实测验证**（进程没了 + 内存回收）。
set -uo pipefail
echo "=== 杀前 ==="
pgrep -af '[_]bk_exp.py' || echo "  （无）"
free -m | head -2

for P in $(pgrep -f '[_]bk_exp.py'); do
  echo "kill -9 $P"
  kill -9 "$P" 2>/dev/null || true
done
sleep 3

echo
echo "=== 杀后 ==="
if pgrep -af '[_]bk_exp.py'; then
  echo "  ⛔ **仍有存活**（需再杀）"
else
  echo "  ✅ 已无 _bk_exp.py 进程"
fi
free -m | head -2
echo
echo "=== 该作业的 launcher 进程（不应残留）==="
pgrep -af '_r733_longab' || echo "  （无）"
