#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_D1_lit.py —— **D1 第一步**：在本地文献库里找"弹性求解器/微力学"相关文献。

D1 要求"每个方法附文献出处（DOI 或可核实引用），不得凭记忆" ⇒ 先扫本地库。
"""
import csv
import os

IDX = "/mnt/f/speed_up/_litidx/index.tsv"
GROUPS = {
    'FFT / 谱法微力学': ['fft', 'spectral', 'fourier', 'green function', 'green\'s function',
                        'periodic', 'Moulinec', 'micromechanic'],
    '夹杂/Eshelby/均匀化': ['eshelby', 'inclusion', 'inhomogeneit', 'homogeni', 'eigenstrain',
                          'transformation strain', 'polarization'],
    '相场弹性': ['phase field', 'phase-field', 'elastic', 'strain energy', 'misfit',
                'eigenstrain', 'khachaturyan'],
    '锐界面/不连续': ['sharp interface', 'discontinu', 'jump condition', 'boundary integral',
                    'level set', 'level-set', 'interface elastic'],
    '位错/偶极表示': ['dislocation', 'dipole', 'misfit dislocation', 'nucleation of dislocation'],
}
rows = list(csv.DictReader(open(IDX, encoding="utf-8", errors="replace"), delimiter="\t"))
print("索引共 %d 条\n" % len(rows))
for g, kws in GROUPS.items():
    kws = [k.lower() for k in kws]
    hits = []
    for r in rows:
        blob = ' '.join(str(r.get(k, '')) for k in ('file', 'title', 'why')).lower()
        n = sum(1 for k in kws if k in blob)
        if n:
            rel = 2 if str(r.get('category', '')).upper() == 'REL' else 0
            hits.append((n + rel, n, r))
    hits.sort(key=lambda t: (-t[0], -t[1]))
    print("=" * 96)
    print("【%s】命中 %d 条" % (g, len(hits)))
    print("=" * 96)
    for s, n, r in hits[:8]:
        print("  [%s] %s" % (r.get('category', '?'), str(r.get('file', ''))[:78]))
        t = str(r.get('title', '')).strip()
        if t:
            print("        %s" % t[:100])
    if not hits:
        print("  （无命中）")
    print()
