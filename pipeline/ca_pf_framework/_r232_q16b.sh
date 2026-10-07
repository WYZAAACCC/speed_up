#!/bin/bash
# _r232_q16b.sh —— 读 `larr` 编码探针的结果。
cd "$(dirname "$0")" || exit 1
grep -n 'Q-16' _w2_r231.log
grep -n '有限计数' _w2_r231.log
grep -n 'karr' _w2_r231.log
grep -n 'larr' _w2_r231.log
grep -n 'vmap' _w2_r231.log
echo "--- 若上面为空，打印三项量级那一段 ---"
grep -n -A10 '三项量级' _w2_r231.log | head -20
