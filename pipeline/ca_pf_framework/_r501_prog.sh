#!/usr/bin/env bash
# R501 —— R498 三臂进度 + 末行
set -u
cd "$(dirname "$0")"
tail -3 _w2_r498_outer.log 2>/dev/null || echo "（outer 未写）"
echo "--- 各臂 ---"
for T in r498D r498E r498F; do
  C="_exp/_bk_mb/dry_${T}/series.csv"
  L="_w2_r498_${T}.log"
  NC=0; [ -f "$C" ] && NC=$(wc -l < "$C")
  NS=0; [ -f "$L" ] && NS=$(grep -c 'qs] 档' "$L" || true)
  NE=0; [ -f "$L" ] && NE=$(grep -c '纯溶解早退' "$L" || true)
  printf '  %-7s 行=%-5s qs档=%-4s 早退=%-4s  末行: ' "$T" "$NC" "$NS" "$NE"
  [ -f "$C" ] && tail -1 "$C" | cut -c1-44
  echo
done
echo "--- 进程数 ---"
pgrep -c -f '_bk_exp' || echo 0
uptime
