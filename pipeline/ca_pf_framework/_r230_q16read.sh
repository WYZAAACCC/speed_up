#!/bin/bash
# _r230_q16read.sh —— 读 Q-16 的定位输出。
cd "$(dirname "$0")" || exit 1
grep -n -E 'Q-16|有限计数|vmap|场→变体|F2 异变体|F3 同变体|F1 含母相|三项量级' \
  _w2_r229.log | tail -20
echo
echo "=== 该臂的块内自检与 t=0 行 ==="
grep -E '块内界面自检|nf3col|F3面' _w2_r229.log | head -4
