#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== m3out10 状态'
tail -3 _w2_r73_run.log 2>/dev/null
d=_exp/_bk_mb/dry_m3out10
if [ -f "$d/series.csv" ]; then
  echo "  step=$(tail -1 "$d/series.csv" | cut -d, -f1)"
  echo '=== O-1/O-4：块结构与撞壁'
  $PY - <<'PY'
import csv, os
p = '_exp/_bk_mb/dry_m3out10/series.csv'
rows = list(csv.DictReader(open(p)))
cs = [c for c in ('step','nslab_n','nf3_col','box_touch_core','Vt') if c in rows[0]]
print('  ' + ' '.join('%-12s' % c for c in cs))
for r in rows[::6][-6:]:
    print('  ' + ' '.join('%-12s' % str(r.get(c,''))[:12] for c in cs))
PY
  echo '=== O-2/O-3：f_flat 与 v_a/v_w'
  timeout 900 $PY _r65_corner.py "$d" 2>&1 | grep -E '首末'
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | grep -E '全程'
else
  echo '  （无产物）'
fi
