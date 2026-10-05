#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10PRT2
L=_w2_t5_short_$TAG.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  pid=$EN"; ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
echo "--- 步 ---"; grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -2 | cut -c1-125
echo "--- 形核/清理/保护 ---"
echo -n "  形核行 = "; grep -ac 'athermal 形核' "$L" 2>/dev/null
echo -n "  播种清理 = "; grep -ac '\[SEEDCLEAN\]' "$L" 2>/dev/null
echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' "$L" 2>/dev/null
echo -n "  SEEDCARVED = "; grep -ac '\[SEEDCARVED\]' "$L" 2>/dev/null
echo -n "  ★ protected 含 0 的行数（应 0）= "; grep -a '\[SEEDCARVED\]' "$L" 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- 判决日志 ---"; tail -28 _w2_t10_prt2_verdict.log 2>/dev/null
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
