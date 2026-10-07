#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== 终态（600 步）f_flat / f_tip'
for t in m3fp10 m3fp0; do
  echo "--- $t"
  timeout 900 $PY _r65_corner.py "_exp/_bk_mb/dry_$t" 2>&1 | grep -E '首末'
done
echo
echo '=== 终态 v2 口径速率'
for t in m3fp10 m3fp0; do
  echo "--- $t"
  timeout 600 $PY _r53_v2run.py "_exp/_bk_mb/dry_$t" 2>&1 | grep -E '全程'
done
echo
echo '=== 块结构 / 撞壁 / 体积'
$PY - <<'PY'
import csv, os
for t in ('m3fp10', 'm3fp0'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    rows = list(csv.DictReader(open(p)))
    r = rows[-1]
    print('  %-8s step=%-4s nslab_n=%-3s nf3_col=%-3s core=%-3s Vt=%s'
          % (t, r['step'], r.get('nslab_n'), r.get('nf3_col'),
             r.get('box_touch_core'), r.get('Vt', '')[:11]))
PY
