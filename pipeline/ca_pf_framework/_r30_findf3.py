#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：在 `_r30_dumpscan.json` 里找 `nf3` 非零的算例（= 有 F3 界面可测）。"""
import json
import csv
import os
import sys

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/r30_dumpscan.json'))
hits = []
for c in D['cases']:
    sc = os.path.join(c['dir'], 'series.csv')
    if not os.path.exists(sc):
        continue
    with open(sc, newline='') as fh:
        r = list(csv.DictReader(fh))
    if not r or 'nf3' not in r[0]:
        continue
    mx = max((float(x['nf3'] or 0) for x in r), default=0.0)
    mxcol = max((float(x.get('nf3_col') or 0) for x in r), default=0.0)
    a = max((float(x.get('f3_area_m2') or 0) for x in r), default=0.0)
    if mx > 0 or mxcol > 0:
        hits.append((mx, mxcol, a, c['dir'], c['nsnap'],
                     'phi' in str(c['keysets']), c['steps']))
hits.sort(reverse=True)
print('%-10s %-8s %-12s %-40s %5s %5s' % ('nf3max', 'nf3col', 'area_m2',
                                          'dir', 'nsnap', 'phi'))
for h in hits:
    print('%-10.0f %-8.0f %-12.3e %-40s %5d %5s' % (h[0], h[1], h[2], h[3],
                                                    h[4], h[5]))
