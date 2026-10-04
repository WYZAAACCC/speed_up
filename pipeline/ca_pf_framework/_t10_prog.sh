#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 步进行 + 节拍（末 8 条）---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null \
  | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -8
echo "--- 末个步进（含块统计相关）---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | cut -c1-200
echo "--- ★ swap ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,time,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else
  echo "  ⚠ 引擎不在"
fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- exit ---"; [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  （无 ⇒ 活着）"
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- auto 尾 ---"; tail -5 _w2_t10_auto.log 2>/dev/null
echo "--- swap 报警尾 ---"; tail -3 _w2_t10_swapalert.log 2>/dev/null
