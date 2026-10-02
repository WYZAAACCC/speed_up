#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_xchk.py --- ★★★★★ 交叉核对：`snap_00200` 的"各变体之和" vs `series.csv` 的 `nslab_n`
                        （P30：同名近名量可能口径不同 ⇒ 必须**分列**对，不许混算）
"""
import csv
import os
import sys
from collections import Counter

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['F', 'G']

print('=' * 100)
print('交叉核对：快照的"变体分组之和" vs `series.csv` 的 `nslab_n` / `nf3_col`')
print('=' * 100)
print(' %-4s %-6s %-10s %-12s %-10s %-10s %s'
      % ('臂', 'step', 'V(快照)', 'Σ各变体', 'nslab_n', 'nf3_col', '一致？'))
print(' ' + '-' * 90)
for t in TAGS:
    d = os.path.join(ROOT, 'dry_' + t)
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        print(' %-4s （无 series.csv）' % t)
        continue
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    hdr = list(rows[0].keys())
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    for sn in snaps:
        st = int(sn.split('_')[1].split('.')[0])
        # 找 series.csv 里最接近这一 step 的行
        row = None
        for r in rows:
            try:
                if int(float(r[hdr[0]])) == st:
                    row = r
            except Exception:
                pass
        if row is None:
            continue
        z = np.load(os.path.join(d, sn))
        if 'region' not in z or 'vmap_keys' not in z:
            continue
        reg = z['region']
        vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                      [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
        by = Counter()
        for f in np.unique(reg):
            f = int(f)
            if f > 0:
                by[vm.get(f, -1)] += 1
        V = len(by)
        tot = sum(by.values())
        ns = row.get('nslab_n', '?')
        nc = row.get('nf3_col', '?')
        ok = ''
        try:
            ok = '✅ 相等' if int(float(ns)) == tot else '⚠ 差 %d' % (tot - int(float(ns)))
        except Exception:
            ok = '（读不到）'
        print(' %-4s %-6d %-10d %-12d %-10s %-10s %s'
              % (t, st, V, tot, ns, nc, ok))
print()
print('  ★ 判读：')
print('   · **相等** ⇒ 两个口径同源 ⇒ 可互推')
print('   · **不等** ⇒ 口径不同（P30）⇒ **必须分列报**，不许拿一个替另一个')
print('=' * 100)
