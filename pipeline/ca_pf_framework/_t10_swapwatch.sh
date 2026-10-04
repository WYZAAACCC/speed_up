#!/bin/bash
# _t10_swapwatch.sh --- 盯进程 + **swap 一旦被触发就报警**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10N160
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- exit 文件（存在 = 已结束）---"
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt; else echo "  （无 ⇒ 引擎活着）"; fi
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
done
if [ -z "$P" ]; then
  echo "⚠ 引擎不在"
  grep -a '看门狗\|峰值 RSS' _w2_t5_short_$TAG.log 2>/dev/null | tail -3
else
  echo "--- 进程 ---"
  ps -o pid,etime,time,pcpu,rss --no-headers -p "$P" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "  %s\n", $0}' /proc/$P/status
  SW=$(awk '/VmSwap/{print $2}' /proc/$P/status)
  echo "  ⇒ 进程 swap = $(( ${SW:-0} / 1024 )) MB"
fi
echo "--- 全机 free ---"; free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- 引擎日志步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | cut -c1-95
echo "  （快照数 = $(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)）"
echo "--- 盯守最后 6 条 ---"
tail -6 _w2_t10_launch28.log 2>/dev/null | sed 's/^/  /'
