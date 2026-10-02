#!/bin/bash
# _r581_snaps.sh --- 列出每个臂手上的快照（含 step 号）
cd "$(dirname "$0")" || exit 1
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps p2_m12 p2_m12b; do
  d="_exp/_bk_p2/dry_$t"
  if [ ! -d "$d" ]; then printf '  %-9s （无目录）\n' "$t"; continue; fi
  sn=$(ls "$d" 2>/dev/null | grep '^snap_' | sort | tr '\n' ' ')
  printf '  %-9s series=%-5s nuc_dbg=%-7s 快照: %s\n' "$t" \
    "$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)" \
    "$([ -f "$d/nuc_dbg.json" ] && stat -c %s "$d/nuc_dbg.json" || echo 0)" \
    "${sn:-（无）}"
done
echo
echo '── 队列日志尾 ──'
tail -3 _w2_r581_mqueue.log 2>/dev/null | sed 's/^/  /'
echo '── 队列进程数 ──'
ps -eo args --no-headers 2>/dev/null | grep _r581_mqueue | grep -vc grep
