#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_vt.py --- ★ 打印各臂的 `Vt` 轨迹（`attach` 模式下 `Vt` 才是长大指标，不是 `nslab_n`）"""
import csv
import os
import sys

for t in (sys.argv[1:] or ['t5H3', 't5G3']):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-6s ⚠ 无 series' % t)
        continue
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    v = [(int(x['step']), float(x['Vt'])) for x in r if (x.get('Vt') or '').strip()]
    print('  ── %s：%d 点 ──' % (t, len(v)))
    print('     %s' % ['%d:%.4g' % (s, y) for s, y in v])
    if len(v) >= 3:
        d = ['%+.3g' % (v[i + 1][1] - v[i][1]) for i in range(len(v) - 1)]
        print('     逐点增量: %s' % d)
        print('     末三: %s ⇒ **%s**'
              % (['%.4g' % y for _, y in v[-3:]],
                 '升 ↑' if v[-1][1] > v[-2][1] else '降 ↓'))
        lo = min(v, key=lambda z: z[1])
        print('     全程最低 %.4g @ step %d；末值/最低 = **%.3f×**'
              % (lo[1], lo[0], v[-1][1] / lo[1]))
