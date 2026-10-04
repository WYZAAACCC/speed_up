#!/bin/bash
# _t10_e253chk.sh --- t10E253 状态（swap / 步 / 事件 / 快照）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
TAG=t10E253
L=_w2_t5_short_$TAG.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,time,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "  %s\n", $0}' /proc/$EN/status
else
  echo "  ⚠ 引擎不在"
fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "  exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)"
echo "--- 步/节拍 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -5
echo "--- 末步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -1 | cut -c1-150
echo "--- 形核事件 ---"
echo "  athermal = $(grep -ac 'athermal 形核' "$L" 2>/dev/null) ；补投轮 = $(grep -ac 's292 补投轮' "$L" 2>/dev/null) ；fresh 被拒 = $(grep -ac 'fresh` 被拒' "$L" 2>/dev/null)"
grep -a 's292 补投轮' "$L" 2>/dev/null | tail -2 | sed 's/^/    /'
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 报警尾 ---"; tail -3 _w2_t10_swapalert253.log 2>/dev/null
echo "--- 自动守望尾 ---"; tail -4 _w2_t10_auto253.log 2>/dev/null
