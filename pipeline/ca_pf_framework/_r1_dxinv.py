#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_dxinv.py --- 把三个算例的**实际配置**列出来，确认 Δx 对照的设计意图。

`_r1_dxconsist.py` 里的 A/B 两臂标签写着"种子 ×2"，而新跑完的
`mid192_s2_ns4` 用的是 `--seed-scale 2`。**必须先确认谁对谁**，
否则会把"Δx 效应"和"种子尺寸效应"混在一起（这正是 §3 记的旧账）。

不猜：直接读每个算例的 `meta.json` + `log.txt` 里的真实命令行与 `cal`。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = ['mid250_ns4', 'mid250_base', 'mid250_ns2', 'mid250_ns1',
        'mid192_ns4', 'mid192_s2_ns4', 'mid192_ns2', 'lath192_ns4']

print('=' * 108)
print('%-16s %5s %8s %6s %6s %8s %9s  %s'
      % ('dir', 'N', 'dx(nm)', 'steps', 'every', 'seed-scl', 'norm_sm', 'case/变体'))
print('=' * 108)
for d in DIRS:
    p = os.path.join(HERE, '_exp', d, 'meta.json')
    if not os.path.exists(p):
        print('%-16s  (no meta.json)' % d)
        continue
    try:
        m = json.load(open(p))
    except Exception as e:                                   # noqa: BLE001
        print('%-16s  meta.json 读不了: %s' % (d, e))
        continue
    g = m.get('args', m)
    cal = m.get('cal', {}) or {}
    nrow = 0
    sp = os.path.join(HERE, '_exp', d, 'series.csv')
    if os.path.exists(sp):
        nrow = sum(1 for _ in open(sp)) - 1
    print('%-16s %5s %8s %6s %6s %8s %9s  %s  rows=%d laststep=%s'
          % (d, g.get('N'), g.get('dx_nm'), g.get('steps'), g.get('every'),
             g.get('seed_scale'), g.get('norm_smooth'),
             '%s/%s' % (g.get('case'), g.get('variants')), nrow,
             (nrow * int(g.get('every') or 4)) if nrow else '-'))
    if cal:
        print('%-16s    cal: %s' % ('', {k: (round(v, 4) if isinstance(v, float)
                                             else v) for k, v in cal.items()}))
print('=' * 108)
