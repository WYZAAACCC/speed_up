#!/bin/bash
# _r203_regread.sh —— 从回归日志里抽出**断言**部分（不看仿真过程刷屏）。
cd "$(dirname "$0")" || exit 1
for f in _w2_r202_regress.log _w2_r30_regress_stdout.log; do
  [ -f "$f" ] || continue
  echo "########## $f （$(wc -l < "$f") 行）##########"
  grep -nE '^[[:space:]]*[①②③④⑤⑥⑦⑧⑨⑩]|PASS|FAIL|✅|❌|逐位|回归|判定|====' "$f" \
    | grep -vE 'WindowB|nslab=|F3面=' | tail -60
  echo
done
