#!/bin/bash
# _bk_watch_events.sh —— 盯 cl1 的 athermal 事件，**5 次全部出现就立刻退出**（不跑完也报）。
# 目的：让"逐根形核温度 T_k 与预言的对比"这条**核心科学判据**尽早到达，
#       不必等 2853 步全跑完。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for i in $(seq 1 240); do          # 240 × 30 s = 2 h 上限
  N=$(grep -ac 'athermal 形核' _w2_bk_cl1.log 2>/dev/null || echo 0)
  # 第 1 行是"★★★ R29 athermal 形核律"的抬头 ⇒ 真事件数 = N − 1
  if [ "$N" -ge 6 ]; then
    echo "=== 5 次事件全部出现（抬头 + 5） ==="
    grep -a 'athermal 形核' _w2_bk_cl1.log
    exit 0
  fi
  if ! pgrep -f 'tag cl1$' > /dev/null 2>&1 && ! pgrep -f 'tag cl1 ' > /dev/null 2>&1; then
    echo "=== cl1 进程已退出（事件数 = $((N-1))） ==="
    grep -a 'athermal 形核' _w2_bk_cl1.log
    exit 0
  fi
  sleep 30
done
echo "=== 2 h 超时（事件数 = $((N-1))） ==="
grep -a 'athermal 形核' _w2_bk_cl1.log
