#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_longest.py --- 补核：**跑完的长跑**是哪几条、什么配置"""
import glob
import json
import os
import time

import csv

recs = []
for d in glob.glob('_exp/**/dry_*', recursive=True):
    if not os.path.isdir(d) or 'superseded' in d:
        continue
    mp, sp = os.path.join(d, 'meta.json'), os.path.join(d, 'series.csv')
    if not (os.path.exists(mp) and os.path.exists(sp)):
        continue
    try:
        m = json.load(open(mp, encoding='utf-8', errors='replace'))
        rows = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace')))
    except Exception:
        continue
    if not rows:
        continue
    k = list(rows[0].keys())[0]
    try:
        last = float(rows[-1][k])
    except Exception:
        continue
    ea = m.get('exp_args')
    if isinstance(ea, str):
        try:
            ea = json.loads(ea.replace("'", '"'))
        except Exception:
            ea = {}
    if not isinstance(ea, dict):
        ea = {}
    want = m.get('steps') or ea.get('steps')
    try:
        want = float(want)
    except Exception:
        want = None
    if want and last / want >= 0.99 and last >= 200:
        recs.append(dict(tag=os.path.basename(d)[4:], dir=d, N=m.get('N'),
                         want=want, last=last, mtime=os.path.getmtime(sp),
                         laths=m.get('laths_n') or ea.get('laths'),
                         nv=len(rows[0].get('vols', '').split('/')) if rows[0].get('vols') else None))
print('=' * 100)
print('★ **跑完（≥99%）且步数 ≥200** 的臂，按步数降序')
print('=' * 100)
print('  %-12s %-6s %-9s %-9s %-13s %s' % ('臂', 'N', '步数', '末步', '末次修改', '目录'))
print('  ' + '-' * 96)
for r in sorted(recs, key=lambda r: -r['last'])[:20]:
    print('  %-12s %-6s %-9.0f %-9.0f %-13s %s' %
          (r['tag'][:12], r['N'], r['want'], r['last'],
           time.strftime('%m-%d %H:%M', time.localtime(r['mtime'])), r['dir']))
print()
print('  ⇒ 共 **%d 条**跑完的长跑' % len(recs))
print('=' * 100)
