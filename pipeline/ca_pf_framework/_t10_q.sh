#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 盯守日志行数 ---"
wc -l _w2_t10_auto.log _w2_t10_swapalert.log 2>/dev/null
echo "--- 引擎 ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else
  echo "  ⚠ 引擎不在"
fi
echo "--- free ---"; free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- exit ---"; [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  （无 ⇒ 活着）"
echo "--- burst 事件 ---"; grep -ac 'athermal 形核' _w2_t5_short_t10N160.log 2>/dev/null
echo "--- 步 ---"; grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -2 | cut -c1-90
