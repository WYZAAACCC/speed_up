#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== 三维图：最大场 168 @ step 100 ==="
$PY _t5_split3d2.py t10N160 168 100 2>&1 | tail -3
echo
echo "=== 内存 ==="
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status; else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "=== 末步 ==="
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | cut -c1-140
echo "=== 快照 ==="
ls _exp/_bk_t5/dry_t10N160/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
