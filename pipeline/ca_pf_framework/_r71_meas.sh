#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== M-1/M-3：f_flat 与 v_a/v_w（step 280 时的读数）'
for t in m3fp10 m3fp0; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || { echo "--- $t 无"; continue; }
  echo "--- $t  ($(tail -1 "$d/series.csv" | cut -d, -f1) 步)"
  timeout 900 $PY _r65_corner.py "$d" 2>&1 | grep -E '^  (0|100|200)\s|首末 f_flat' | head -5
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | grep -E '^全程' | head -2
done
echo
echo '=== M-2/M-4：块结构 / 撞壁 / 体积'
$PY - <<'PY'
import csv, os
for t in ('m3fp10', 'm3fp0'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p)))
    r = rows[-1]
    print('  %-8s step=%-4s nslab_n=%-3s nf3_col=%-3s box_touch_core=%-3s Vt=%s'
          % (t, r['step'], r.get('nslab_n'), r.get('nf3_col'),
             r.get('box_touch_core'), r.get('Vt', '')[:10]))
PY
