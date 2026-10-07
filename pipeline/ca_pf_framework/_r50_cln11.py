#!/usr/bin/env python3
"""R50: cln11（athermal 形核臂）事件与柱结构读数。用法: python _r50_cln11.py"""
import csv
import json
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
print('=== cln11 nuc_dbg.json（athermal 形核事件）')
p = '_exp/_bk_closed/dry_cln11/nuc_dbg.json'
if os.path.exists(p):
    d = json.load(open(p))
    print(json.dumps(d, ensure_ascii=False, indent=1)[:2000])
else:
    print('(无)')
print()
print('=== cln11 series.csv 关键列（形核事件应表现为 nslab/M 的阶梯）')
rows = list(csv.DictReader(open('_exp/_bk_closed/dry_cln11/series.csv')))
cols = [c for c in ('step', 'M', 'nslab_n', 'nf3_col', 'Vt', 'nf3', 'f3_area_m2',
                    'E_el_J', 'v_tip_nabs', 'tip_sep_nm') if c in rows[0]]
print('  ' + ' '.join('%-12s' % c for c in cols))
for r in rows[::4] + [rows[-1]]:
    print('  ' + ' '.join('%-12s' % str(r.get(c, ''))[:12] for c in cols))
