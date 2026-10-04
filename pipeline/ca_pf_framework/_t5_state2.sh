#!/bin/bash
# Precise state: argv, cwd, snapshot times with date, log times.
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== NOW ==="; date '+%Y-%m-%d %H:%M:%S'
echo
echo "=== PROCESSES (full argv) ==="
ps -eo pid,ppid,etime,lstart,args --no-headers | grep '_bk_exp.py' | grep -v grep | while read -r line; do
  PID=$(echo "$line" | awk '{print $1}')
  echo "--- PID $PID ---"
  echo "$line" | sed 's/^\(.\{40\}\).*\(--N .*\)/\1 ... \2/' | cut -c1-600
  echo "  cwd: $(readlink /proc/$PID/cwd 2>/dev/null)"
done
echo
echo "=== SNAPSHOT mtimes (with date) ==="
for T in t5FIX t5ETAo t5BKMo; do
  D=_exp/_bk_t5/dry_$T
  echo "--- $T ---"
  ls -la --time-style=+%m-%d_%H:%M:%S $D/snap_*.npz 2>/dev/null | awk '{print $6, $7}' | tail -4
  echo "  count=$(ls $D/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo "=== LOG mtimes ==="
ls -la --time-style=+%m-%d_%H:%M:%S _w2_t5_short_t5FIX.log _w2_t5_short_t5ETAo.log _w2_t5_short_t5BKMo.log _w2_t5_t5FIX.log _w2_t5_ablate.log 2>/dev/null | awk '{print $6, $7, $5}'
echo
echo "=== t5FIX log: real step lines only (last 6) ==="
grep -a '^\s*\[ *[0-9]*\]' _w2_t5_short_t5FIX.log 2>/dev/null | tail -6 | cut -c1-190
echo
echo "=== t5ETAo log: real step lines only (last 4) ==="
grep -a '^\s*\[ *[0-9]*\]' _w2_t5_short_t5ETAo.log 2>/dev/null | tail -4 | cut -c1-190
echo
echo "=== t5BKMo log: real step lines only (last 4) ==="
grep -a '^\s*\[ *[0-9]*\]' _w2_t5_short_t5BKMo.log 2>/dev/null | tail -4 | cut -c1-190
echo
echo "=== t5BKMo rejection summary ==="
grep -ac '被引擎拒' _w2_t5_short_t5BKMo.log 2>/dev/null
grep -a '被引擎拒' _w2_t5_short_t5BKMo.log 2>/dev/null | tail -1 | cut -c1-160
