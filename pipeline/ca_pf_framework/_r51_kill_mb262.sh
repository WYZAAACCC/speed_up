#!/bin/bash
# R51: 杀掉已知超界的 `eng_mb2_62` 冒烟（12 层 7.62 µm 装不进 6 µm 盒）
#   只匹配唯一标识 `--tag mb2_62`（§24 教训 #2：不匹配公共参数）。
set -u
K=0
for P in $(pgrep -f -- '--tag mb2_62' 2>/dev/null); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P : $(echo "$CMD" | cut -c1-60)"; kill -9 "$P"; K=1 ;;
    *) echo "skip $P" ;;
  esac
done
[ "$K" = 0 ] && echo "（没找到 --tag mb2_62 的进程）"
sleep 2
echo "--- 残留"
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-64
