#!/usr/bin/env python3
"""R50: cln11 的 `Vt` 在 step ~2000 从 7.4 掉到 1.0 µm³ —— 是物理还是 bug？
判据（预先写死）：
  A. 若是**数值/记账**问题（同时刻 `V0` 也掉、或 `region` 变空）⇒ bug；
  B. 若是**物理**（冷却时某根板条被母相吞回 / 变体重选）⇒ `nslab_n` 应同步下降，
     且 `Vt` 的减少应与**某一根场**的体积减少对应。
"""
import csv
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
rows = list(csv.DictReader(open('_exp/_bk_closed/dry_cln11/series.csv')))
print('=== step 1800–2400 逐行（每 100 步一采）')
cols = ['step', 't_s', 'dt', 'V0', 'Vt', 'M', 'nslab_n', 'nf3_col', 'ncomp_min',
        'ncomp_max', 'vols']
cols = [c for c in cols if c in rows[0]]
print('  ' + ' '.join('%-13s' % c for c in cols))
for r in rows:
    st = int(r['step'])
    if 1700 <= st <= 2500:
        print('  ' + ' '.join('%-13s' % str(r.get(c, ''))[:13] for c in cols))
print()
print('=== 全程 Vt 的相邻差（找所有"塌陷"）')
prev = None
for r in rows:
    v = float(r['Vt'])
    if prev is not None:
        d = v - prev
        if abs(d) > 0.15 * max(abs(prev), 1e-30):
            print('  step %-5s  Vt %+.4f → %+.4f  (Δ=%+.4f, %+.1f%%)  nslab=%s nf3col=%s'
                  % (r['step'], prev, v, d, 100 * d / prev, r['nslab_n'], r['nf3_col']))
    prev = v
print()
print('=== 每根场的体积轨迹（vols，µm³）')
idx = [i for i, r in enumerate(rows) if int(r['step']) % 800 == 0]
for i in idx + [len(rows) - 1]:
    r = rows[i]
    print('  step %-5s  nslab=%s  vols=%s' % (r['step'], r['nslab_n'], r['vols'][:70]))
