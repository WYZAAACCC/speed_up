#!/bin/bash
# _r581_run_recollect.sh --- 跑证据收集并打印判据行（避免引号地狱）
cd "$(dirname "$0")" || exit 1
timeout 1200 bash _r581_recollect.sh > /dev/null 2>&1
echo "recollect exit=$?"
echo
echo '── 各判据的"差异字段数"──'
grep -E '^判据：|差异字段数' _w2_r581_evidence.log 2>/dev/null
