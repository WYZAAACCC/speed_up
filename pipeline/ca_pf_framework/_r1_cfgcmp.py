#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_cfgcmp.py --- 把几个臂的**关键配置**并排列出来（避免拿不可比的臂作比较）。

`_r1_c5chk.py` 显示同为 Δx=125、nseed=1 的三个 mid 臂 `fill_cal` 末值差很多
（0.499 / 0.638 / 0.718）⇒ 差异**不是分辨率**造成的。
本脚本把 `norm_smooth`、`seed_scale`、步数等并排列出，找出真正的差别。
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = ['mid1', 'mid192_ns1', 'mid192_ns2', 'mid192_ns4', 'mid192_s2_ns4',
        'mid250_base', 'mid250_ns1', 'mid250_ns2', 'mid250_ns4']
KEYS = ['N', 'dx_nm', 'steps', 'nseed', 'seed_scale', 'norm_smooth',
        'adv', 'nthreads', 'variants']

print('=' * 112)
rows = []
for d in ARMS:
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    sp = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(mp):
        print('%-14s （无 meta.json）' % d)
        continue
    try:
        m = json.load(open(mp))
    except Exception as e:                                       # noqa: BLE001
        print('%-14s meta 读不了：%s' % (d, e)); continue
    nrow = 0
    lastfc = float('nan')
    if os.path.exists(sp):
        rr = list(csv.DictReader(open(sp)))
        nrow = len(rr)
        for r in reversed(rr):
            try:
                lastfc = float(r['fill_cal'])
                break
            except (TypeError, ValueError, KeyError):
                continue
    rows.append((d, m, nrow, lastfc))

hdr = '%-14s' % '臂' + ''.join('%13s' % k for k in KEYS) + '%8s %10s' % ('rows', 'fc末')
print(hdr)
print('-' * 112)
for d, m, nrow, lastfc in rows:
    print('%-14s' % d + ''.join('%13s' % m.get(k) for k in KEYS)
          + '%8d %10s' % (nrow, ('%.3f' % lastfc) if lastfc == lastfc else '—'))
print('=' * 112)
