#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== F-1：f_flat（末值与衰减）'
timeout 900 $PY _r65_corner.py _exp/_bk_mb/dry_fp20 2>&1 | tail -8
echo
echo '=== F-2：v_a/v_w（v2 口径）'
timeout 600 $PY _r53_v2run.py _exp/_bk_mb/dry_fp20 2>&1 | tail -3
echo
echo '=== F-4：撞壁'
$PY - <<'PY'
import csv, os
p = '_exp/_bk_mb/dry_fp20/series.csv'
if os.path.exists(p):
    rows = list(csv.DictReader(open(p)))
    for c in ('box_touch', 'box_touch_core'):
        if c in rows[0]:
            print('  %s: %s' % (c, sorted({r[c] for r in rows})))
    print('  末 step=%s  Vt=%s' % (rows[-1]['step'], rows[-1]['Vt']))
PY
