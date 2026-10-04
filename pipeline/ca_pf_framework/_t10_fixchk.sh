#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10FIX
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
echo -n "  形核事件 = "; grep -ac 'athermal 形核' _w2_t5_short_$TAG.log 2>/dev/null
echo -n "  SEEDCLEAN 行 = "; grep -ac '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null
grep -a '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null | head -5 | sed 's/^/    /'
echo "--- 步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -2 | cut -c1-120
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 报警尾 ---"; tail -3 _w2_t10_swapfix.log 2>/dev/null
