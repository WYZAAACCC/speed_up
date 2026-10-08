#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_Ms_spectrum.py —— 在**全库**已提取文本里找 Ti-6Al-4V 的 M_s 实测值（只读）。"""
import io
import os
import re
import sys

ROOTS = ['/mnt/f/speed_up/_litidx/lit_txt_all', '/mnt/f/speed_up/_litidx/lit_txt',
         '/mnt/f/speed_up/_litidx/lit_txt_r712']
seen = set()
rows = []
RX = re.compile(r'(M\s*s|martensite start|martensitic start)', re.I)
VAL = re.compile(r'(\d{3,4})\s*(?:°|/C176|\xb0)?\s*C\b|(\d{3,4})\s*K\b')
for R in ROOTS:
    if not os.path.isdir(R):
        continue
    for fn in sorted(os.listdir(R)):
        if not fn.endswith('.txt') or fn in seen:
            continue
        seen.add(fn)
        L = io.open(os.path.join(R, fn), encoding='utf-8', errors='replace').read().splitlines()
        for i, s in enumerate(L, 1):
            if RX.search(s):
                vals = VAL.findall(s)
                if vals:
                    rows.append((fn, i, s.strip()[:160], vals))

print('扫描了 %d 个 txt；含 "M_s + 温度值" 的行：%d' % (len(seen), len(rows)))
print('=' * 100)
for fn, i, s, vals in rows[:60]:
    vv = ','.join((a or b) for a, b in vals)
    print('  %-46s :%-5d [%s]  %s' % (fn[:46], i, vv, s[:110]))
sys.exit(0)
