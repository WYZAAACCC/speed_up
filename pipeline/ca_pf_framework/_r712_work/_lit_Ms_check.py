#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_Ms_check.py —— C：核 `M_s` 的原始出处（只读）。

三个候选值：
  A) 873 K  = 600 °C  —— 代码 `windowB_km.py:93 M_S_TI64 = 873.0`，标 [L] Ji 2016
  B) 1115 K = 842 °C  —— `LITPARAM_TI64_MARTENSITE_ANCHORS.md:15` 的"片段直引"
  C) 848 K            —— `WINDOWB_PARAMS §1`（另一条线，见代码注释）

核法：把 Ji 2016（`s11669-015-0436-9.pdf`）抽文本，搜 M_s / Ms / 600 / 842 的上下文。
"""
import io
import os
import re
import sys

SRC = '/mnt/f/参考论文/马氏体仿真'
OUT = '/mnt/f/speed_up/_litidx/lit_txt_all'
os.makedirs(OUT, exist_ok=True)

TARGETS = ['s11669-015-0436-9.pdf']      # Ji 2016
# 顺便把"可能有 Ms 值"的几篇一起抽
KEYS = ['s11669-015-0436-9', 'Martensite-formation-in-titanium-alloys',
        'Achieving-ultra-high-strength-of-laser-powder-bed-fusion-Ti']


def safe(f):
    return re.sub(r'[^\w.\-]', '_', f)[:150]


def extract(path):
    try:
        import pypdf
        R = pypdf.PdfReader(path)
        return '\n'.join((p.extract_text() or '') for p in R.pages)
    except Exception:
        return None


pdfs = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.pdf'))
sel = []
for k in KEYS:
    for f in pdfs:
        if k.lower() in f.lower():
            sel.append(f)
            break

PATS = [
    ('Ms-600C', r'600\s*°?\s*C|600\s*C\b|873\s*K'),
    ('Ms-842C', r'842\s*°?\s*C|1115\s*K'),
    ('Ms-848K', r'848\s*K|575\s*°?\s*C'),
    ('Ms-词', r'\bM\s*s\b|martensite start|M_s|MＳ'),
    ('临界驱动力', r'1200\s*J/mol|critical driving force|driving force.{0,40}Ms'),
]

for f in sel:
    p = os.path.join(SRC, f)
    txt = extract(p)
    if txt is None:
        print('✗ 提取失败：%s' % f)
        continue
    o = os.path.join(OUT, safe(f) + '.txt')
    io.open(o, 'w', encoding='utf-8').write(txt)
    L = txt.splitlines()
    print()
    print('=' * 96)
    print('● %s（%d 行）' % (f[:88], len(L)))
    for tag, pat in PATS:
        rx = re.compile(pat, re.I)
        got = [(i, s.strip()) for i, s in enumerate(L, 1) if rx.search(s)]
        print('   [%s] %d 行' % (tag, len(got)))
        for i, s in got[:8]:
            print('      :%-5d %s' % (i, s[:150]))
sys.exit(0)
