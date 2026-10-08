#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR708_citecheck.py —— 机械化复验 `R714_CHECKLIST_COMPLETED.md` 里的每一处
`文件.py:行号` 引用是否落在文件行数范围内，并抽验若干条的实际内容。

只读；不改任何文件。
运行： cd /mnt/f/speed_up/pipeline/ca_pf_framework
       /root/miniconda3/envs/ml/bin/python -u _auditR708_citecheck.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, 'R714_CHECKLIST_COMPLETED.md')
SRC = ['_bk_exp.py', 'windowB_surface.py', 'windowB_lath.py', 'windowB_km.py',
       '_bk_measure.py', 'windowB_ti64_variants.py', '_r68_facet_op.py',
       'prod_boxB.py', 'prod_boxB_mob.py', 'windowB_b1.py']

srcs = {}
for fn in SRC:
    p = os.path.join(HERE, fn)
    srcs[fn] = io.open(p, encoding='utf-8').read().splitlines()

doc = io.open(DOC, encoding='utf-8').read()
pat = re.compile(r'([A-Za-z_][A-Za-z0-9_]*\.py):(\d+)(?:-(\d+))?')
pats = set()
for m in pat.finditer(doc):
    lo = int(m.group(2))
    hi = int(m.group(3)) if m.group(3) else None
    pats.add((m.group(1), lo, hi))

bad = []
for fn, lo, hi in sorted(pats, key=lambda t: (t[0], t[1], t[2] or 0)):
    if fn not in srcs:
        bad.append((fn, lo, hi, 'FILE-NOT-LOCAL'))
        continue
    n = len(srcs[fn])
    if lo > n or (hi and hi > n):
        bad.append((fn, lo, hi, 'OUT-OF-RANGE(total=%d)' % n))

print('=' * 78)
print('引用复验：报告里共 %d 条 "file.py:line" 引用' % len(pats))
print('  越界 / 无法核对： %s' % (bad if bad else '无 OK'))
print('=' * 78)
print('抽验实际内容：')
spot = [('_bk_exp.py', 81), ('_bk_exp.py', 2630), ('_bk_exp.py', 2639),
        ('_bk_exp.py', 3589), ('_bk_exp.py', 1601),
        ('windowB_surface.py', 3792), ('windowB_surface.py', 3795),
        ('windowB_surface.py', 2888), ('windowB_surface.py', 1958),
        ('windowB_surface.py', 1963), ('windowB_surface.py', 3303), ('windowB_surface.py', 3308),
        ('_r68_facet_op.py', 83), ('_r68_facet_op.py', 92),
        ('windowB_ti64_variants.py', 173), ('_bk_measure.py', 1092)]
for fn, a in spot:
    if fn in srcs and 1 <= a <= len(srcs[fn]):
        print('  %-26s %6d: %s' % (fn, a, srcs[fn][a - 1].strip()[:96]))
    else:
        print('  %-26s %6d: <不可用>' % (fn, a))
sys.exit(1 if bad else 0)
