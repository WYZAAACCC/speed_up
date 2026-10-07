#!/bin/bash
# _r197_wait.sh —— 轮询 R165 直到 step 400（或超时）。**只读，不杀任何东西。**
cd "$(dirname "$0")" || exit 1
F=_exp/_bk_mb/dry_saSet2F2/series.csv
G=_exp/_bk_mb/dry_saOddGF2/series.csv
i=0
while [ "$i" -lt 40 ]; do
  i=$((i + 1))
  s1=$(tail -1 "$F" 2>/dev/null | cut -d, -f1)
  s2=$(tail -1 "$G" 2>/dev/null | cut -d, -f1)
  n=$(pgrep -fc '_bk_exp[.]py' 2>/dev/null)
  n=${n:-0}
  echo "poll $i: saSet2F2=$s1 saOddGF2=$s2  procs=$n"
  if [ "$s1" = "400" ] && [ "$s2" = "400" ]; then
    echo "TERMINAL: 两臂都到 400"
    break
  fi
  if [ "$n" = "0" ]; then
    echo "NO PROCS: 进程都没了（可能已结束或崩了）"
    break
  fi
  sleep 30
done
echo "--- 末行 ---"
tail -2 "$F"
