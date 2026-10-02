#!/bin/bash
# _r581_postmortem.sh --- ★ `p2_b5ov` 进程消失的**事后取证**。
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T') ==="
echo "── 当前所有臂进程 ──"
ps -eo pid,etime,rss,args --no-headers 2>/dev/null | grep _r581_p2 | grep -v grep | cut -c1-110
echo "  计数 = $(ps -eo args --no-headers 2>/dev/null | grep _r581_p2 | grep -vc grep)"
echo
echo "── 守卫 ──"
for f in _w2_r581_softguard.log _w2_r581_memguard.log; do
  echo "  [$f]"
  tail -4 "$f" 2>/dev/null | sed 's/^/     /'
done
echo
echo "── 两臂的产物进度 ──"
for t in p2_b5ov p2_b5ps; do
  d="_exp/_bk_p2/dry_$t"
  if [ -d "$d" ]; then
    printf '  %-9s series=%-5s 快照=%s\n' "$t" \
      "$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)" \
      "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
  else
    printf '  %-9s （无目录）\n' "$t"
  fi
done
echo
echo "── b5ov 日志尾（判死因）──"
tail -2 _w2_r581_p2_p2_b5ov.log | cut -c1-130
echo "  行数 = $(wc -l < _w2_r581_p2_p2_b5ov.log)"
echo "  Traceback = $(grep -c '^Traceback' _w2_r581_p2_p2_b5ov.log)"
echo "  MemoryError/OOM = $(grep -ciE 'memoryerror|cannot allocate|killed' _w2_r581_p2_p2_b5ov.log)"
echo
echo "── 系统层有没有 OOM / 杀进程记录 ──"
dmesg 2>/dev/null | grep -iE 'killed process|out of memory' | tail -4 | sed 's/^/     /'
echo "  （空 = 没有内核 OOM 记录）"
echo
echo "── 内存现状 ──"
free -m | sed -n 2p | awk '{printf "  已用 %s MB  可用 %s MB\n",$3,$7}'
