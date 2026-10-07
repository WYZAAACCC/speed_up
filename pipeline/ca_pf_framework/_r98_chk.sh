#!/bin/bash
# _r98_chk.sh —— R98 播种冒烟判读
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
tail -3 _w2_r98_run.log
echo
for t in saOdd700 saOdd1000 saEven700 saEven1000; do
  L="_w2_r98_${t}.log"
  [ -f "$L" ] || { echo "--- $t （无日志）"; continue; }
  echo "--- $t"
  grep -E "R31 多块播种|精确判据|播种后|多块：块心|^   块[0-9]：" "$L" | head -14
  echo "    step0 读数： $(grep -m1 '\[   0\]' "$L" | cut -c1-150)"
  # step 0 的 nf2 从 CSV 取（比打印更全：覆盖所有异变体对）
  /root/miniconda3/envs/ml/bin/python - "$t" <<'PY'
import csv, os, sys
t = sys.argv[1]
p = '_exp/_bk_mb/dry_%s/series.csv' % t
if not os.path.exists(p):
    print('    （无 series.csv）'); raise SystemExit
rows = list(csv.DictReader(open(p)))
r0 = rows[0]
print('    **step0: nf2=%s  nblk_sig=%s  blk_vars=%s  blk_laths=%s  runs=%s**'
      % (r0.get('nf2'), r0.get('nblk_sig'), r0.get('blk_vars'),
         r0.get('blk_laths'), r0.get('runs')))
r1 = rows[-1]
print('    末行(%s): nf2=%s nslab_n=%s Vt=%.4f µm³'
      % (r1.get('step'), r1.get('nf2'), r1.get('nslab_n'),
         float(r1.get('Vt', 0)) * 1e18))
PY
done
