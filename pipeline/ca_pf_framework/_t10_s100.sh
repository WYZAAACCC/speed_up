#!/bin/bash
# 等 step 100 快照，一到就出七项
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
sleep 840
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo "--- 快照 ---"
ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- 步/节拍 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null \
  | grep -oE '^ *\[ *[0-9]+\]|[0-9.]+s/步' | paste - - | tail -5
echo "--- 末步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | cut -c1-185
echo "--- swap ---"
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status; else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
[ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo "  exit: 无"
echo
echo "════ 七项监控（若有 step 100 快照）════"
MX=$(ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then
  $PY _t10_seven.py t10N160 "$MX" 2>&1 | head -45
else
  echo "  快照最大 = ${MX:-0}，还没到 100 ⇒ 下一轮再来"
  $PY _t10_seven.py t10N160 2>&1 | tail -8
fi
