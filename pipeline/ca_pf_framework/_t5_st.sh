#!/bin/bash
# _t5_st.sh --- 长跑状态速查（只看真正在用的日志）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,rss,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep \
  | awk '{printf "  pid=%s 已跑=%s RSS=%.1fGB\n", $1, $2, $3/1048576}' | sed 's/^/  /'
echo '── 两臂引擎日志尾部 ──'
for t in t5L62 t5L0; do
  f="_w2_t5_short_$t.log"
  printf '  %-6s %s\n' "$t" "$([ -f "$f" ] && stat -c '%s 字节' "$f" || echo '（还没生成）')"
  tail -2 "$f" 2>/dev/null | cut -c1-118 | sed 's/^/        /'
done
echo '── 编排器日志尾部 ──'
tail -4 _w2_t5_long.log 2>/dev/null | sed 's/^/  /'
echo '── 内存 ──'
free -m | sed -n 2p | sed 's/^/  /'
echo '── 产物 ──'
for t in t5L62 t5L0; do
  d=_exp/_bk_t5/dry_$t
  printf '  %-6s series=%s 行  ckpt=%s 个  snap=%s 个\n' "$t" \
    "$(wc -l < "$d/series.csv" 2>/dev/null || echo 0)" \
    "$(ls -1 "$d/ckpt" 2>/dev/null | wc -l)" \
    "$(ls -1 "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
