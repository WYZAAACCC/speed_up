#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW $(date '+%m-%d %H:%M:%S') ==="
echo "--- 所有相关进程 ---"
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_*) printf "  pid=%-6s %s\n" "$P" "$(echo "$C" | cut -c1-95)" ;;
  esac
done
echo "--- 引擎 ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o pid,etime,time,pcpu --no-headers -p "$EN" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "    %s\n", $0}' /proc/$EN/status
else
  echo "    ⚠ 引擎不在"
fi
free -m | sed -n '2,3p' | sed 's/^/    /'
echo "--- exit 文件 ---"
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "    （无 ⇒ 活着）"
echo "--- burst 事件数 / 末条 ---"
echo "    athermal 行 = $(grep -ac 'athermal 形核' _w2_t5_short_t10N160.log 2>/dev/null)"
grep -a 'athermal 形核' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | grep -oE 'step [0-9]+.*累计 [0-9]+/[0-9]+' | cut -c1-95 | sed 's/^/    /'
echo "--- 步进行 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -3 | cut -c1-100 | sed 's/^/    /'
echo "    快照 = $(ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | wc -l)"
