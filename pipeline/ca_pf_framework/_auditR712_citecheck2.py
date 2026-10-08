#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR712_citecheck2.py —— 复验 R712 补齐稿里引用的行号（只读）。"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(HERE, 'R712_REVISION_SUPPLEMENT.md')
SRC = ['_bk_exp.py', 'windowB_surface.py', 'windowB_lath.py', 'windowB_km.py',
       '_bk_measure.py', 'windowB_ti64_variants.py', '_r68_facet_op.py',
       '_auditR708_facetproj.py', '_r45_facechk.py',
       '_auditR712_check.py', '_auditR712_verify.py',
       '../../pipeline/RESEARCH_INTENT.md', 'README.md']

srcs = {}
for fn in SRC:
    p = fn if os.path.isabs(fn) else os.path.join(HERE, fn)
    if os.path.exists(p):
        srcs[os.path.basename(fn)] = io.open(p, encoding='utf-8').read().splitlines()

doc = io.open(DOC, encoding='utf-8').read()
pat = re.compile(r'([A-Za-z_][A-Za-z0-9_\-]*\.(?:py|md|csv)):(\d+)(?:-(\d+))?')
pats = set()
for m in pat.finditer(doc):
    pats.add((m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None))

bad = []
for fn, lo, hi in sorted(pats, key=lambda t: (t[0], t[1], t[2] or 0)):
    if fn not in srcs:
        bad.append((fn, lo, hi, 'NOT-CHECKED'))
        continue
    n = len(srcs[fn])
    if lo > n or (hi and hi > n):
        bad.append((fn, lo, hi, 'OUT-OF-RANGE(total=%d)' % n))

print('补齐稿里共 %d 条 file:line 引用' % len(pats))
print('越界： %s' % (bad if bad else '无'))
print()
print('抽验实际内容：')
spot = [('windowB_surface.py', 5100), ('windowB_surface.py', 5104),
        ('windowB_surface.py', 4078), ('windowB_surface.py', 4080),
        ('windowB_surface.py', 5144), ('windowB_surface.py', 5256),
        ('RESEARCH_INTENT.md', 269), ('_r45_facechk.py', 1)]
for fn, n in spot:
    if fn in srcs and 1 <= n <= len(srcs[fn]):
        print('  %-22s %5d: %s' % (fn, n, srcs[fn][n - 1].strip()[:96]))
    else:
        print('  %-22s %5d: <不可用>' % (fn, n))
sys.exit(1 if bad else 0)
