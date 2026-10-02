#!/bin/bash
# _r581_p2stat.sh --- 长跑状态一屏（尾部若干行 + 关键计数 + 内存）
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T') ==="
free -m | sed -n 2p
ps -eo pid,etime,pcpu,rss,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | \
  awk '{printf "  pid=%s 运行=%s cpu=%s%% rss=%.2fGB\n", $1,$2,$3,$4/1048576}'
echo "  合计 RSS: $(ps -eo rss,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | awk '{s+=$1} END {printf "%.2f GB", s/1048576}')"
for t in p2_b5 p2_b3; do
  f="_w2_r581_p2_$t.log"
  echo "--- $t ---"
  [ -f "$f" ] || { echo "  (无日志)"; continue; }
  echo "  行数=$(wc -l < "$f")  最后一行:"
  tail -1 "$f" | cut -c1-200
  echo "  形核事件数=$(grep -c 'athermal 形核' "$f")  被拒=$(grep -c '被引擎拒' "$f")"
  echo "  df 首次/末次: $(grep -o 'df=[0-9.eE+-]*' "$f" | head -1)  $(grep -o 'df=[0-9.eE+-]*' "$f" | tail -1)"
  echo "  Traceback=$(grep -c '^Traceback' "$f")"
done
