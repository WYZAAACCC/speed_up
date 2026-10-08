#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r724_lit_wide.py —— **S6 的放宽检索**（`P28`：别把"我的正则太窄"当成"文献里没有"）。

对 217 篇抽取文本跑**更宽的词表**，逐个统计**文件数**（不是行数），
并打印命中上下文，便于人工判读"到底有没有 Ti64 α′ 的生长动力学数据"。
"""
import os
import re
import sys

D = sys.argv[1] if len(sys.argv) > 1 else '/mnt/f/speed_up/_litidx/lit_txt_all'

GROUPS = [
    ('A. 界面迁移率/速度（宽）',
     r'(mobilit|migration\s+of\s+the\s+interface|interface\s+mobilit|'
     r'kinetic\s+coefficient|interface\s+velocity|growth\s+velocity|'
     r'growth\s+kinetics|transformation\s+kinetics)'),
    ('B. 激活能（宽）', r'(activation\s+energy|activation\s+enthalpy|Q\s*=\s*\d+\s*kJ)'),
    ('C. Ti64 语境（宽）', r'(Ti\s*[-–—]?\s*6\s*Al\s*[-–—]?\s*4\s*V|Ti64|Ti-6Al-4V|Ti6Al4V)'),
    ('D. α′ 马氏体（宽）', r'(martensit|α\s*[\'′]|alpha\s*prime|α′|acicular|hcp\s+α)'),
    ('E. 生长速率带数值', r'(\d+(\.\d+)?\s*[×x]?\s*10\s*[\^−\-]?\s*\d*\s*(m\s*/\s*s|m/s|µm/s|nm/s|mm/s))'),
    ('F. 板条生长（宽）', r'(lath\s+growth|growth\s+of\s+(the\s+)?lath|plate\s+growth|'
                          r'thickening\s+kinetics|length\s+growth)'),
    ('G. 界面能/迁移率各向异性', r'(anisotrop\w*\s+(of\s+)?(the\s+)?(interface|mobilit|energy|growth))'),
]

files = sorted(f for f in os.listdir(D) if f.endswith('.txt'))
print('=' * 104)
print('S6 放宽检索（%s，%d 篇）' % (D, len(files)))
print('=' * 104)
pat = {name: re.compile(rx, re.I) for name, rx in GROUPS}
count = {name: 0 for name, _ in GROUPS}
ti_files = set()
hit_ex = {name: [] for name, _ in GROUPS}
for f in files:
    try:
        txt = open(os.path.join(D, f), encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    is_ti = bool(pat['C. Ti64 语境（宽）'].search(txt))
    if is_ti:
        ti_files.add(f)
    for name, _ in GROUPS:
        m = pat[name].search(txt)
        if m:
            count[name] += 1
            if len(hit_ex[name]) < 4:
                s = max(0, m.start() - 70)
                hit_ex[name].append((f, txt[s:m.end() + 90].replace('\n', ' ')))

print('\n## 逐组命中文件数')
for name, _ in GROUPS:
    print('  %-34s %4d 篇' % (name, count[name]))
print('\n  ★ 含 Ti64 语境的文献共 **%d 篇 / %d**' % (len(ti_files), len(files)))

print('\n## ★★ 关键交叉：**Ti64 语境** ∧ (A 界面迁移率/速度 或 B 激活能)')
n_cross = 0
for f in sorted(ti_files):
    try:
        txt = open(os.path.join(D, f), encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    a = pat['A. 界面迁移率/速度（宽）'].search(txt)
    b = pat['B. 激活能（宽）'].search(txt)
    if a or b:
        n_cross += 1
        print('\n  【%s】' % f[:88])
        for tag, m in (('A', a), ('B', b)):
            if m:
                s = max(0, m.start() - 80)
                print('     %s: …%s…' % (tag, txt[s:m.end() + 110].replace('\n', ' ')))
print('\n  ⇒ **Ti64 语境 ∧ (迁移率 or 激活能) = %d 篇**' % n_cross)

print('\n## 示例上下文（每组的头几条）')
for name, _ in GROUPS:
    if not hit_ex[name]:
        continue
    print('\n  === %s ===' % name)
    for f, ctx in hit_ex[name][:2]:
        print('    【%s】' % f[:70])
        print('       …%s…' % ctx[:190])
