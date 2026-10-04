#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 步/节拍 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null \
  | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -4
echo "--- 末步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | cut -c1-150
echo "--- swap / 内存 ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
echo "--- 快照 ---"; ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
MX=$(ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
if [ -n "$MX" ] && [ "${MX:-0}" -ge 200 ] 2>/dev/null; then
  echo "════ 七项 @ step $MX ════"
  $PY _t10_seven.py t10N160 "$MX" 2>&1 | sed -n '4,30p'
fi
