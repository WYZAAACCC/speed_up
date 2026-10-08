#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_r712_scan.py —— 在已提取的文献全文里找"形核率/位点密度"的**定量**语句。

只读。输出：命中文件 + 行号 + 原文片段（供人工判读）。
用法： cd /mnt/f/speed_up && /root/miniconda3/envs/ml/bin/python -u _lit_r712_scan.py
"""
import io
import os
import re
import sys

ROOT = '/mnt/f/speed_up/_litidx/lit_txt'
PATTERNS = [
    ('率-通用', r'nucleation rate|rate of nucleation'),
    ('位点密度', r'site density|density of nucleation sites|number of nucleation sites|'
                r'nucleation site density|N_?v\b|N<sub>v'),
    ('位点饱和', r'site saturat|saturation of nucleation sites|sites are consumed|'
                r'exhaust(ion|ed) of (nucleation )?sites'),
    ('自催化', r'autocataly'),
    ('athermal', r'athermal'),
    ('KM/唯象', r'Koistinen|Marburger|K-M equation|kinetics of martensite'),
    ('经典形核率式', r'exp\s*\(\s*[-−]\s*Δ?G\s*\*?\s*/\s*k|'
                    r'exp\s*\(\s*[-−]\s*\\?Delta ?G\s*\*?\s*/\s*k|'
                    r'steady[- ]state nucleation|cluster dynamics'),
    ('Poisson/随机', r'Poisson|stochastic (nucleation|process)|random (nucleation|seed)'),
    ('板条厚度-形核', r'lath (width|thickness).{0,80}(nucleat|number|density)|'
                     r'(nucleat|density).{0,80}lath (width|thickness)'),
]

files = sorted(f for f in os.listdir(ROOT) if f.endswith('.txt'))
print('扫描目录：%s' % ROOT)
print('文件数：%d' % len(files))
print('=' * 100)

summary = []
for fn in files:
    p = os.path.join(ROOT, fn)
    try:
        L = io.open(p, encoding='utf-8', errors='replace').read().splitlines()
    except OSError:
        continue
    hits = {}
    for tag, pat in PATTERNS:
        rx = re.compile(pat, re.I)
        got = [(i, s.strip()) for i, s in enumerate(L, 1) if rx.search(s)]
        if got:
            hits[tag] = got
    if hits:
        summary.append((fn, hits))

# 汇总：按"命中了几个不同类别"降序
summary.sort(key=lambda t: (-len(t[1]), t[0]))
print('\n【汇总】命中的文件与类别数')
for fn, hits in summary:
    print('  %-2d 类  %s' % (len(hits), fn[:96]))
    for tag in hits:
        print('          · %s (%d 行)' % (tag, len(hits[tag])))

print()
print('=' * 100)
print('【明细】只打印"率-通用 / 位点密度 / 位点饱和"三类，各前 3 条')
print('=' * 100)
KEY = ('率-通用', '位点密度', '位点饱和')
for fn, hits in summary:
    rows = []
    for tag in KEY:
        for i, s in hits.get(tag, [])[:3]:
            rows.append('      [%s] :%d  %s' % (tag, i, s[:150]))
    if rows:
        print('\n  ● %s' % fn[:100])
        for r in rows:
            print(r)
sys.exit(0)
