#!/usr/bin/env bash
# _r367_readrepl.sh -- 读复现日志的 §174 permB1 段
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== 四个任务的标题行 ==="
grep -n '^# §' _w2_r366.log
echo
echo "=== permB1 的 §174 段（从行号起）==="
LN=$(grep -n 'permB1_200 200' _w2_r366.log | head -1 | cut -d: -f1)
sed -n "${LN},\$p" _w2_r366.log | head -40
