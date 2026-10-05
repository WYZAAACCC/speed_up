#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10CL2
L=_w2_t5_short_$TAG.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
echo -n "  形核事件 = "; grep -ac 'athermal 形核' "$L" 2>/dev/null
echo -n "  播种清理 [SEEDCLEAN] = "; grep -ac '\[SEEDCLEAN\]' "$L" 2>/dev/null
echo "  ★ 周期清理 [SEEDCLEAN-STEP]（独有成功串）："
grep -a '\[SEEDCLEAN-STEP\]' "$L" 2>/dev/null | tail -6 | sed 's/^/    /'
echo -n "  周期清理行数 = "; grep -ac '\[SEEDCLEAN-STEP\]' "$L" 2>/dev/null
echo "--- 步（tail 两次一致性）---"
A=$(grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -1)
sleep 3
B=$(grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -1)
echo "$A" | cut -c1-135
[ "$A" != "$B" ] && echo "  ⚠ 不一致 ⇒ 再读：$(echo "$B" | cut -c1-135)"
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 盯守尾 ---"; tail -4 _w2_t10_swapfix2.log 2>/dev/null
