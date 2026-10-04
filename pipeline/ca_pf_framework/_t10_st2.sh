#!/bin/bash
# _t10_st2.sh --- 10um 算例状态（含退出码）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- ★ 退出码 ---"
if [ -f _w2_t10_exit.txt ]; then cat _w2_t10_exit.txt; else echo "  （无 ⇒ 引擎仍活着）"; fi
echo "--- 引擎进程 ---"
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu,rss,pmem --no-headers -p "$P"
  echo "  VmHWM=$(awk '/VmHWM/{print $2}' /proc/$P/status) kB"
else
  echo "  ⚠ 不在"
fi
echo "--- relaunch 尾 ---"; tail -6 _w2_t10_relaunch.log
echo "--- 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | cut -c1-100
echo "--- 事件/补投轮 ---"
echo "  s292 补投轮 = $(grep -ac 's292 补投轮' _w2_t5_short_t10N160.log 2>/dev/null)"
grep -a 's292 补投轮' _w2_t5_short_t10N160.log 2>/dev/null | tail -2
echo "  athermal 行 = $(grep -ac 'athermal' _w2_t5_short_t10N160.log 2>/dev/null)"
echo "--- 快照 ---"
ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l
echo "--- free ---"; free -m | sed -n 2p
