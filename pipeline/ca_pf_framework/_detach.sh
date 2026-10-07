#!/usr/bin/env bash
# _detach.sh --- 把一条命令**彻底脱离**调用它的 shell/pwsh 进程树（setsid + nohup）。
# ★ 记账（本轮踩的坑）：之前用 `nohup ... &` 起的两条长作业（T16 正规跑 / T13b）
#   在会话被中断后**随 pwsh 进程一起消失**（两次都只剩表头、没有数据行）。
#   ⇒ 改用 `setsid`：新会话首进程，父进程变成 init ⇒ 调用方怎么死都不影响它。
#   用法：bash _detach.sh <logfile> <cmd...>
set -u
LOG="$1"; shift
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
setsid nohup "$@" > "$LOG" 2>&1 < /dev/null &
PID=$!
disown 2>/dev/null || true
echo "detached pid=$PID log=$LOG"
