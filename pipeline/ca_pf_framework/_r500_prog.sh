#!/usr/bin/env bash
# R500 —— R498 三臂进度查看
set -u
cd "$(dirname "$0")"
tail -4 _w2_r498_outer.log 2>/dev/null || echo "（outer 还没写）"
echo "--- 各臂 ---"
for T in r498D r498E r498F; do
  C="_exp/_bk_mb/dry_${T}/series.csv"
  L="_w2_r498_${T}.log"
  NC=0; [ -f "$C" ] && NC=$(wc -l < "$C")
  NE=0; [ -f "$L" ] && NE=$(grep -c '纯溶解早退' "$L" || true)
  NS=0; [ -f "$L" ] && NS=$(grep -c 'qs] 档' "$L" || true)
  printf '  %-8s CSV=%-5s qs档=%-4s 早退=%-4s\n' "$T" "$NC" "$NS" "$NE"
done
echo "--- 进程 ---"
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep '[_]bk_exp' | cut -c1-62
uptime
