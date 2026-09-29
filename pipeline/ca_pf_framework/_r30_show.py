#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：把 `_r30_dumpscan.py` 的 JSON 里指定算例的细节打出来。"""
import json
import sys

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/r30_dumpscan.json'))
want = sys.argv[2:] or [
    '_exp/_bk_closed/dry_cl1b', '_exp/_bk_eng/eng_eng12',
    '_exp/_bk_time/dry_nc3', '_exp/e7_selfac', '_exp/_bk_block/dry_p1',
    '_exp/_bk_f3smoke/main', '_exp/_bk_closed/dry_cln2',
    '_exp/lath192_ns4', '_exp/_bk_closed/dry_cl1', '_exp/_bk_closed/dry_cl1g',
]
for c in D['cases']:
    if c['dir'] not in want:
        continue
    print('##### %s  nsnap=%d  %.2f MB' % (c['dir'], c['nsnap'],
                                          c['bytes'] / 1e6))
    for k in c['keysets']:
        print('   keys x%-3d: %s' % (k['n'], k['keys']))
    print('   steps: %s' % c.get('steps'))
    print('   dstep: %s' % c.get('dstep'))
    cols = c.get('csv_cols') or []
    print('   csv_rows=%s  ncols=%d' % (c.get('csv_rows'), len(cols)))
    print('   csv_cols: %s' % cols)
    print('   other: %s' % c.get('other'))
    if c.get('errors'):
        print('   errors: %s' % c['errors'])
    print()
