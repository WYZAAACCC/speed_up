#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR712_final_check.py —— 终版文档的**引用复验**（只读）。

做两件事：
  A. 对一份**抽验表**（SPOT）逐条打印 `文件:行号` 的实际内容 ⇒ 人工可核"引用有没有指错地方"
  B. 对**三份终版文档**里的**全部** `file:line` 引用做越界检查：
       `R712_FINAL_GUIDE_v2.md` / `R712_REPAIR_SPEC.md` / `R714_FINAL_PROBLEMS.md`
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(HERE, 'R712_FINAL_GUIDE_v2.md')

SPOT = [
    ('_bk_exp.py', 81), ('_bk_exp.py', 2019), ('_bk_exp.py', 2044), ('_bk_exp.py', 2134),
    ('_bk_exp.py', 2630), ('_bk_exp.py', 2639), ('_bk_exp.py', 2943), ('_bk_exp.py', 2944),
    ('_bk_exp.py', 3589), ('_bk_exp.py', 4152), ('_bk_exp.py', 4552), ('_bk_exp.py', 4668),
    ('_bk_exp.py', 4706), ('_bk_exp.py', 4739),
    ('windowB_surface.py', 1128), ('windowB_surface.py', 1253), ('windowB_surface.py', 1564),
    ('windowB_surface.py', 2207), ('windowB_surface.py', 2537), ('windowB_surface.py', 2707),
    ('windowB_surface.py', 2817), ('windowB_surface.py', 3262), ('windowB_surface.py', 3298),
    ('windowB_surface.py', 3355), ('windowB_surface.py', 3371), ('windowB_surface.py', 3792),
    ('windowB_surface.py', 3795), ('windowB_surface.py', 4094), ('windowB_surface.py', 4139),
    ('windowB_surface.py', 4308), ('windowB_surface.py', 4674), ('windowB_surface.py', 4873),
    ('windowB_surface.py', 5100), ('windowB_surface.py', 5104), ('windowB_surface.py', 5256),
    ('windowB_surface.py', 5271), ('windowB_surface.py', 5690),
    ('_bk_measure.py', 373), ('_bk_measure.py', 1092), ('_bk_measure.py', 1440),
    ('windowB_lath.py', 158), ('windowB_lath.py', 186), ('windowB_km.py', 138),
    ('windowB_ti64_variants.py', 172),
    ('_r68_facet_op.py', 83),
    ('R2_PARAM_VERDICTS.md', 694), ('R707_PHYSICAL_CORRECTNESS_AUDIT.md', 18),
    ('../../pipeline/RESEARCH_INTENT.md', 269),
]

srcs = {}
for fn, n in SPOT:
    p = fn if os.path.isabs(fn) else os.path.join(HERE, fn)
    key = os.path.basename(fn)
    if key not in srcs and os.path.exists(p):
        srcs[key] = io.open(p, encoding='utf-8').read().splitlines()

bad = []
print('=' * 96)
print('抽验 %d 处引用的实际内容' % len(SPOT))
print('=' * 96)
for fn, n in SPOT:
    key = os.path.basename(fn)
    L = srcs.get(key)
    if L is None:
        bad.append((fn, n, 'FILE-MISSING'))
        print('  %-34s %5d  <文件不存在>' % (fn, n))
        continue
    if n > len(L):
        bad.append((fn, n, 'OUT-OF-RANGE(%d)' % len(L)))
        print('  %-34s %5d  <越界，总行 %d>' % (fn, n, len(L)))
        continue
    s = L[n - 1].strip()
    print('  %-34s %5d  %s' % (fn, n, s[:76] if s else '<BLANK>'))

print()
print('=' * 96)
print('终版文档的 file:line 引用越界检查（对 R712_REPAIR_SPEC.md 做一遍）')
print('=' * 96)
local = {}
for d in (HERE, os.path.join(ROOT, 'pipeline')):
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(('.py', '.md', '.csv', '.i')):
                local.setdefault(f, os.path.join(d, f))
for DOCNAME in ('R712_FINAL_GUIDE_v2.md', 'R712_REPAIR_SPEC.md',
                'R714_FINAL_PROBLEMS.md'):
    dp = os.path.join(HERE, DOCNAME)
    if not os.path.exists(dp):
        print('  （%s 尚未写出，跳过）' % DOCNAME)
        continue
    d2 = io.open(dp, encoding='utf-8').read()
    pat2 = re.compile(r'([A-Za-z_][A-Za-z0-9_.\-]*\.(?:py|md|csv|i)):(\d+)(?:[-\u2013](\d+))?')
    seen2 = set()
    for m in pat2.finditer(d2):
        seen2.add((m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
    oob2 = []
    for fn, lo, hi in sorted(seen2, key=lambda t: (t[0], t[1], t[2] or 0)):
        p = local.get(fn)
        if p is None:
            oob2.append((fn, lo, 'FILE-NOT-LOCAL'))
            continue
        nn = len(io.open(p, encoding='utf-8', errors='replace').read().splitlines())
        if lo > nn or (hi and hi > nn):
            oob2.append((fn, lo, hi, 'OUT-OF-RANGE(%d)' % nn))
    print('  %-26s 共 %3d 条引用；越界：%s'
          % (DOCNAME, len(seen2), oob2 if oob2 else '无'))

print()
print('=' * 96)
print('抽验失败项： %s' % (bad if bad else '无'))
print('=' * 96)
sys.exit(1 if bad else 0)
