#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== R75 状态'
tail -4 _w2_r75_run.log 2>/dev/null
echo
echo '=== B-2/B-4/B-5 终态'
$PY - <<'PY'
import csv, os
for t in ('mb2fp10', 'mb2fp0'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-9s （无）' % t); continue
    rows = list(csv.DictReader(open(p)))
    last = rows[-1]
    nf = [float(r['nf2']) for r in rows if r.get('nf2') not in (None, '')]
    print('  %-9s step=%-4s nslab=%-3s nf3col=%-3s nf2: %s→%s  单调=%-5s core=%-3s Vt=%s'
          % (t, last['step'], last['nslab_n'], last['nf3_col'],
             ('%.0f' % nf[0]) if nf else '?', ('%.0f' % nf[-1]) if nf else '?',
             (all(b >= a for a, b in zip(nf, nf[1:])) if nf else '?'),
             last.get('box_touch_core'), last['Vt'][:9]))
PY
echo
echo '=== E_el_J 的单位：看引擎 E_el() 的定义'
grep -n 'def E_el' -A 12 windowB_pf3d.py 2>/dev/null | head -16
