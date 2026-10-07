#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== R75 状态'
tail -4 _w2_r75_run.log 2>/dev/null
echo
echo '=== B-2/B-4/B-5：nf2 / 撞壁 / 自协调量'
$PY - <<'PY'
import csv, os
for t in ('mb2fp10', 'mb2fp0'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-9s （无）' % t); continue
    rows = list(csv.DictReader(open(p)))
    cs = [c for c in ('step','nslab_n','nf3_col','nf2','f2_area_m2',
                      'box_touch_core','E_el_J','r_selfac') if c in rows[0]]
    print('--- %s (step %s)' % (t, rows[-1]['step']))
    print('  ' + ' '.join('%-11s' % c for c in cs))
    for r in rows[::6][-4:] + [rows[-1]]:
        print('  ' + ' '.join('%-11s' % str(r.get(c, ''))[:11] for c in cs))
    nf = [float(r['nf2']) for r in rows if r.get('nf2') not in (None, '')]
    if nf:
        mono = all(b >= a for a, b in zip(nf, nf[1:]))
        print('  nf2: 首=%.0f 末=%.0f 单调增=%s' % (nf[0], nf[-1], mono))
    print()
PY
echo '=== B-3：f_flat 终态'
for t in mb2fp10 mb2fp0; do
  d="_exp/_bk_mb/dry_$t"
  [ -f "$d/series.csv" ] || continue
  printf -- '--- %s\n' "$t"
  timeout 900 $PY _r65_corner.py "$d" 2>&1 | grep -E '首末'
done
