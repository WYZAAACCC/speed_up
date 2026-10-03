#!/bin/bash
# _t5_snapq.sh --- 诊断：为什么还没有 snap_01200？（不是轮询，是解一个具体问题）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 两臂末步 ──'
for t in t5H3 t5V2; do
  printf '  %-5s 末步 = %s\n' "$t" "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo
echo '── t5H3 的快照（末 6 个）与哪些带 band ──'
PY=/root/miniconda3/envs/ml/bin/python
for S in $(ls -1 _exp/_bk_t5/dry_t5H3/snap_*.npz 2>/dev/null | sort | tail -6); do
  H=$($PY -c "
import numpy as np
with np.load('$S',allow_pickle=False) as z: print('Y' if 'band_fld' in z.files else 'N')
" 2>/dev/null)
  printf '  %-52s band=%s\n' "$(basename $S)" "$H"
done
echo
echo '── 参数确认：snap-every 与 phi-band-every ──'
grep -oE "snap-every', '[0-9]+'|phi-band-every', [^,]+" _w2_t5_short_t5H3.log 2>/dev/null | head -3 | sed 's/^/  /'
grep -n "phi-band-every" _t5_short.py | head -2 | cut -c1-110 | sed 's/^/  /'
