#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：哪些算例的 `psi_mean` 列是**有限值**（⇒ 该算例的 ψ 是活的）。"""
import csv
import glob
import os

rows = []
for f in sorted(glob.glob('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/'
                          '*/*/series.csv') +
                glob.glob('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/'
                          '*/series.csv')):
    try:
        with open(f, newline='') as fh:
            r = list(csv.DictReader(fh))
    except Exception:                                            # noqa: BLE001
        continue
    if not r or 'psi_mean' not in r[0]:
        continue
    fin = [x['psi_mean'] for x in r
           if x['psi_mean'] not in ('', 'nan', 'NaN')]
    if fin:
        rows.append((f.replace('/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/',
                               ''), len(r), len(fin), fin[0], fin[-1]))
print('有 psi_mean 列且**出现了有限值**的算例：%d 个' % len(rows))
print('%-46s %6s %6s %-22s %-22s' % ('dir', 'rows', 'finite', 'first', 'last'))
for d, n, nf, a, b in rows:
    print('%-46s %6d %6d %-22s %-22s' % (d, n, nf, a, b))
