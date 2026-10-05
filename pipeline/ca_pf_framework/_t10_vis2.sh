#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for K in 111 10; do
  $PY _t5_split3d2.py t10CL2 $K 100 2>&1 | tail -1
done
echo "--- swap ---"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10CL2 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status; else echo "  引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
