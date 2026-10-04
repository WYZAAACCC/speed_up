#!/bin/bash
# Check code state + all arm progress. Read-only.
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

echo "=== [1] live windowB_surface.py ==="
ls -la windowB_surface.py
sha256sum windowB_surface.py | cut -c1-16
echo -n "ed_eta occurrences: "
grep -c 'ed_eta' windowB_surface.py
echo -n "supercrit stack/attach probe lines: "
grep -c 'sc_stack_pass\|sc_att_pass' windowB_surface.py

echo
echo "=== [2] backups ==="
ls -la windowB_surface.py.bak_* 2>/dev/null

echo
echo "=== [3] job list ==="
ps -eo pid,etime,args --no-headers | grep '_bk_exp.py' | grep -v grep | sed 's/\(.\{200\}\).*/\1/'

echo
echo "=== [4] arm progress (max snapshot) ==="
for T in t5FIX t5ETAo t5BKMo t5N276F t5BK1 t5ETA; do
  D=_exp/_bk_t5/dry_$T
  if [ -d "$D" ]; then
    LAST=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
    CNT=$(ls $D/snap_*.npz 2>/dev/null | wc -l)
    MT=$(ls -la --time-style=+%H:%M:%S $D/snap_*.npz 2>/dev/null | tail -1 | awk '{print $6}')
    echo "$T: max=$LAST n=$CNT lastwrite=$MT"
  else
    echo "$T: (no dir)"
  fi
done

echo
echo "=== [5] recent log tails ==="
for T in t5FIX t5ETAo t5BKMo; do
  echo "--- $T ---"
  tail -3 _w2_t5_short_$T.log 2>/dev/null
done

echo
echo "=== [6] waitfix job ==="
ls -la _w2_t5_waitfix.log 2>/dev/null && tail -5 _w2_t5_waitfix.log 2>/dev/null
