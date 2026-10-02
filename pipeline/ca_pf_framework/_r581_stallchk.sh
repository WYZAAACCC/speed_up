#!/bin/bash
# _r581_stallchk.sh --- ★★★ 判"是不是卡住了"（**不只看进程表**，P29）
#   查四样：① 现在几点 ② 日志最后修改时间 ③ 日志最后一条**非空**行 ④ CSV 的最后修改时间
cd "$(dirname "$0")" || exit 1
echo "=== ① 现在 ==="
date '+%F %T'
echo
echo "=== ② 各产物的最后修改时间（与"现在"比）==="
for f in _w2_r581_p2_p2_b5ov.log _w2_r581_p2_p2_b5ps.log \
         _exp/_bk_p2/dry_p2_b5ov/series.csv _exp/_bk_p2/dry_p2_b5ps/series.csv; do
  if [ -f "$f" ]; then
    printf '  %-46s %s\n' "$f" "$(date -r "$f" '+%F %T')"
  fi
done
echo
echo "=== ③ 日志最后 6 条**非空**行 ==="
for t in p2_b5ov p2_b5ps; do
  echo "  ── $t ──"
  grep -v '^[[:space:]]*$' "_w2_r581_p2_${t}.log" 2>/dev/null | tail -6 | cut -c1-150 | sed 's/^/    /'
done
echo
echo "=== ④ CSV 最后 2 行（step + 关键列）==="
for t in p2_b5ov p2_b5ps; do
  f="_exp/_bk_p2/dry_${t}/series.csv"
  [ -f "$f" ] || continue
  echo "  ── $t ──"
  head -1 "$f" | awk -F, '{for(i=1;i<=NF;i++) if($i=="step"||$i=="wall_s"||$i=="nslab_n"||$i=="Vt") printf "%s=%d ", $i, i; print ""}'
  tail -2 "$f" | cut -c1-120 | sed 's/^/    /'
done
echo
echo "=== ⑤ Worker 的 CPU 时间（两次采样，判有没有在算）==="
for p in $(ps -eo pid,args --no-headers 2>/dev/null | grep '_bk_exp\.py' | grep -v grep | awk '{print $1}'); do
  a=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  echo "  pid=$p cpu_jiffies=$a"
done
