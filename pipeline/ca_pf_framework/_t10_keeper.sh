#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for F in _t5_mon_keeper.sh _t5_keeper_all.sh; do
  echo "════════ $F ════════"
  if [ -f "$F" ]; then
    echo "  --- 头部注释（用途）---"
    head -20 "$F" | cut -c1-160
    echo "  --- ★ 杀进程段 ---"
    grep -n 'kill\|TAG\|tag\|bk_exp\|pgrep\|ps -' "$F" | cut -c1-165
  else
    echo "  （不存在）"
  fi
  echo
done
