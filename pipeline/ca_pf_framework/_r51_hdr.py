#!/usr/bin/env python3
"""R51: `n_lath` 到底是**个数**还是**厚度**？—— 打原始表头 + 原始值，不猜。"""
import csv
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
p = '_exp/_bk_closed/dry_cln11/series.csv'
rows = list(csv.DictReader(open(p)))
hdr = list(rows[0].keys())
print('表头共 %d 列：' % len(hdr))
for i, h in enumerate(hdr):
    print('  %2d %s' % (i, h))
print()
r0, rl = rows[0], rows[-1]
print('=== step 0')
for k in ('n_lath', 'w_lath', 'a_lath', 'ths', 'nslab_n', 'M', 'vols'):
    print('  %-8s = %s' % (k, str(r0.get(k, '(无此列)'))[:120]))
print('=== step %s' % rl['step'])
for k in ('n_lath', 'w_lath', 'a_lath', 'ths', 'nslab_n', 'M'):
    print('  %-8s = %s' % (k, str(rl.get(k, '(无此列)'))[:120]))
