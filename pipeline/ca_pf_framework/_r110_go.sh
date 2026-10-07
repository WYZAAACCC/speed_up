#!/bin/bash
# _r110_go.sh —— 安全地清干净残留 `_bk_exp` 进程，再启动 R110 三臂。
#
# ⚠ **为什么要有这个脚本**：上一条命令里我写了 `pkill -f "_r103_selfac"`，
#   而**那条命令自己的命令行里就含这个字符串** ⇒ **shell 被自己 SIGKILL**
#   （退出码 1、没有任何输出、`>` 重定向都没发生）。
#   这正是 `AGENTS.md §3.10` 记过的坑（`pkill -f` 会杀掉自己）——**本轮又踩了一次**。
#
# 正确做法（本脚本）：
#   * 用**方括号技巧** `_bk_exp[.]py` —— 模式文本与自身不匹配；
#   * 先打印再杀，杀完**复核**；
#   * 顺带查 `(deleted)` 僵尸 cwd（`§3.11`）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

echo "=== 清场 $(date '+%F %T')"
PIDS=$(pgrep -f '_bk_exp[.]py' 2>/dev/null || true)
if [ -n "$PIDS" ]; then
  for P in $PIDS; do
    CWD=$(readlink /proc/$P/cwd 2>/dev/null || echo '?')
    echo "  kill pid=$P cwd=$CWD"
    kill -9 "$P" 2>/dev/null || true
  done
else
  echo "  （没有残留）"
fi
sleep 3
LEFT=$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)
echo "  杀后剩余：$LEFT"
echo "  内存：$(free -g | awk 'NR==2{print $7" GB available"}')"

echo
echo "=== 启动 R110 三臂 $(date '+%F %T')"
bash _r110_selfac2.sh
echo "=== R110 全部结束 $(date '+%F %T')"
