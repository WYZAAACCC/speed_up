#!/usr/bin/env python3
"""_r459_boxtouch.py —— 读两臂的 `box_touch` / `box_touch_core`（回答"碰盒子怎么办"）。"""
import csv
import os

P = print
for tag in ('dry_abB', 'dry_abA'):
    p = os.path.join('_exp/_bk_mb', tag, 'series.csv')
    P('\n[%s]' % tag)
    if not os.path.exists(p):
        P('  ✗ 无')
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    keys = [k for k in ('step', 'box_touch', 'box_touch_core', 'ncomp_all',
                        'core_vox', 'Vt') if k in rows[0]]
    P('  %s' % ' | '.join('%-14s' % k for k in keys))
    for r in rows[::max(1, len(rows) // 8)] + [rows[-1]]:
        cells = []
        for k in keys:
            v = r.get(k, '')
            try:
                f = float(v)
                cells.append('%-14.4g' % (f * 1e18 if k == 'Vt' else f))
            except (TypeError, ValueError):
                cells.append('%-14s' % str(v)[:14])
        P('  %s' % ' | '.join(cells))
