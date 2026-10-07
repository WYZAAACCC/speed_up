#!/bin/bash
# R49 自检：`_r30_regress.sh` 到底有没有跑**当前**代码？
#   症状：regress2 的日志里"未参与比较的新列"**没有** `dG_tip_p90` / `v_tip_nabs`
#   ⇒ 要么它复用了旧产物，要么它的列清单是别处来的。
#   判据：直接看它产出的 CSV 表头里有没有新列 + 看它的 mtime。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== regress 脚本里的根/标签'
grep -nE 'ROOT=|TAG=|--tag|--out|rm -rf' _r30_regress.sh | head -20
echo
echo '=== 找 r30reg 的产物目录'
for d in $(find _exp -maxdepth 2 -type d -name '*r30reg*' 2>/dev/null); do
  echo "--- $d"
  ls -la "$d" | head -8
  if [ -f "$d/series.csv" ]; then
    echo "    mtime=$(stat -c %y "$d/series.csv" | cut -c1-19)"
    echo -n "    新列: "
    head -1 "$d/series.csv" | tr ',' '\n' | grep -cE '^(dG_tip_p90|v_tip_nabs|n_tip)$'
    head -1 "$d/series.csv" | tr ',' '\n' | grep -E '^(dG_tip_p90|v_tip_nabs|n_tip|band)' | tr '\n' ' '
    echo
  fi
done
echo
echo '=== 归档 eng12 的表头（对比基准）'
find _exp -maxdepth 2 -type d -name '*eng12*' | head -2
