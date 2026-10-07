#!/bin/bash
# R51: 杀掉方案 B 的失败冒烟（两块在 t=0 重叠，nf2=692）
set -u
K=0
for P in $(pgrep -f -- '--tag b62' 2>/dev/null); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P : $(echo "$CMD" | cut -c1-56)"; kill -9 "$P"; K=1 ;;
    *) echo "skip $P" ;;
  esac
done
[ "$K" = 0 ] && echo "（没找到 --tag b62）"
sleep 2
echo "--- 残留"
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-56
