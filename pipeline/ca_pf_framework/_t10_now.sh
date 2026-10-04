#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- ★ 退出码 ---"
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt; else echo "  （无 ⇒ 引擎仍活着）"; fi
echo "--- ★ 引擎进程 + VmHWM（单调峰值，采样漏不掉）---"
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu,rss --no-headers -p "$P"
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "  %s\n", $0}' /proc/$P/status
  echo "  argv: $(tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-nthreads [0-9]+|\-\-mem-limit-gb [0-9.]+|\-\-N [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+' | tr '\n' ' ')"
  echo "  亲和性: $(taskset -pc $P 2>/dev/null | sed 's/.*list: //')"
else
  echo "  ⚠ 引擎不在"
fi
echo "--- ★ 看门狗是否触发过（引擎日志收尾摘要）---"
grep -a '看门狗\|峰值 RSS' _w2_t5_short_t10N160.log 2>/dev/null | tail -4
echo "--- 盯守轨迹尾 ---"
tail -10 _w2_t10_relaunch2.log 2>/dev/null
echo "--- 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | cut -c1-105
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l
echo "--- free ---"; free -m | sed -n '2,3p'
