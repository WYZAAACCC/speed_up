#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- ★ swap 报警盯守是否在跑 ---"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_t10_swapalert|bk_exp' | grep -v grep | cut -c1-110
echo
echo "--- ★ swap 报警日志（全文）---"
cat _w2_t10_swapalert.log 2>/dev/null
echo
echo "--- ★ 当前进程实况 ---"
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu,rss --no-headers -p "$P"
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "  %s\n", $0}' /proc/$P/status
else
  echo "  ⚠ 引擎不在"
fi
echo "--- free ---"; free -m | sed -n '2,3p'
echo "--- exit 文件 ---"
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt; else echo "  （无 ⇒ 活着）"; fi
echo "--- 步进行 / 快照 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -3 | cut -c1-110
echo "  快照 = $(ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l)"
echo "--- 看门狗摘要（若已结束）---"
grep -a '看门狗\|峰值 RSS' _w2_t5_short_t10N160.log 2>/dev/null | tail -3
