#!/bin/bash
# _bk_chain2.sh —— 无人值守：等四个闭环算例跑完 → 自动出完整证据包。
#   ⚠ 上一版 `_bk_closed_chain.sh` 会在等完之后**再起一次同名 clctrl**（同名目录双写）
#     ⇒ 已废弃。本版**只等不启**，所有算例由调用方先行起好。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_bk_chain2.log
: > "$LOG"

wait_for () {   # $1 = tag 的精确形式（带上 --tag 前缀避免子串误匹配）
  while pgrep -f -- "tag $1 " > /dev/null 2>&1; do sleep 60; done
}

{
  echo "=== $(date '+%F %T') 等 cl1b / cl1gb / clctrlb / cln2 ==="
  for T in cl1b cl1gb clctrlb cln2; do
    wait_for "$T"
    echo "    $(date '+%T') $T 结束"
  done
  echo "=== $(date '+%F %T') 全部结束，出证据包 ==="
} >> "$LOG" 2>&1

bash _bk_closed_verdict.sh cl1b clctrlb >> "$LOG" 2>&1
echo "=== CHAIN2 DONE $(date '+%F %T') ===" >> "$LOG"
