#!/usr/bin/env python3
"""R50: cln11 的**真实末态**（用于更正 §26 —— 我此前只读到 step 6000）。"""
import csv
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
rows = list(csv.DictReader(open('_exp/_bk_closed/dry_cln11/series.csv')))
cols = ['step', 'nslab_n', 'nf3_col', 'ncompbig_max', 'ncomp_max', 'box_touch',
        'nf3', 'f3_area_m2', 'Vt', 'M']
cols = [c for c in cols if c in rows[0]]
print('  末 5 行：')
print('  ' + ' '.join('%-11s' % c for c in cols))
for r in rows[-5:]:
    print('  ' + ' '.join('%-11s' % str(r.get(c, ''))[:11] for c in cols))
print()
last = rows[-1]
print('=== 末态判读（step %s）' % last['step'])
runsl = [int(x) for x in last.get('runs', '').split('/') if x]
print('  M=%s（场数）  nslab_n=%s（段数）  去重场数=%s'
      % (last['M'], last['nslab_n'], len(set(runsl))))
print('  nf3_col=%s  ncompbig_max=%s（≥32 体素的显著分量）  ncomp_max=%s（含孤儿）'
      % (last['nf3_col'], last['ncompbig_max'], last['ncomp_max']))
print('  box_touch(旧口径)=%s' % last['box_touch'])
print('  Vt=%.1f µm³  占盒 %.1f%%'
      % (float(last['Vt']) * 1e18, 100 * float(last['Vt']) * 1e18 / 1718.0))
print()
mx = max(int(r['nslab_n']) for r in rows)
mxu = max(len({int(x) for x in r.get('runs', '').split('/') if x}) for r in rows)
print('  全程最大值: nslab_n=%s  去重场数=%s  (M=%s)' % (mx, mxu, last['M']))
print('  ⇒ 结论：**未铺满 M 根**；末态有 %s 个显著分量 ⇒ **是部分堆叠，不是完美块**'
      % last['ncompbig_max'])
