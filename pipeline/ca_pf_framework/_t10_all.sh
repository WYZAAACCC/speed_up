#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10N160.log
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- ★ swap ---"
echo "  进程 VmSwap / VmHWM / VmRSS / Threads:"
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  ps -o pid,etime,time,pcpu,rss --no-headers -p "$P" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "    %s\n", $0}' /proc/$P/status
else
  echo "    ⚠ 引擎不在"
fi
free -m | sed -n '2,3p' | sed 's/^/    /'
echo "  swap 报警日志尾部："
tail -4 _w2_t10_swapalert.log 2>/dev/null | sed 's/^/    /'
echo "--- ★ burst / 事件进度 ---"
echo "    athermal 形核 行数 = $(grep -ac 'athermal 形核' "$L" 2>/dev/null)"
grep -a 'athermal 形核' "$L" 2>/dev/null | tail -2 \
  | grep -oE 'step [0-9]+：T=[0-9.]+ K.*累计 [0-9]+/[0-9]+；模式 \*\*[a-z]+\*\*；累计 fresh=[0-9]+ stack=[0-9]+' | cut -c1-130 | sed 's/^/    /'
echo "--- ★ 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -4 | cut -c1-115 | sed 's/^/    /'
echo "    快照 = $(ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l)"
echo "--- ★ exit / 看门狗 ---"
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "    （无 exit ⇒ 活着）"
grep -a '看门狗\|峰值 RSS' "$L" 2>/dev/null | tail -2 | sed 's/^/    /'
echo "--- 数据目录最近写入 ---"
ls -la --time-style=+%H:%M:%S _exp/_bk_t5/dry_t10N160/ 2>/dev/null | tail -4 | sed 's/^/    /'
