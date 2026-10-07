#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_litscan.py —— 为阶段 D5（板条厚度定标机制）在**本地文献库**里批量检索。

D5 要求"每条机制附出处" ⇒ 本工具按机制关键词批量查 `_litidx/index.tsv`，
把命中条目按相关度（REL 优先、标题含关键词数）排序输出，供人工核定引用。
"""
import csv
import os
import re

IDX = "/mnt/f/speed_up/_litidx/index.tsv"
# 按"可能的厚度控制机制"分组检索（D5 要逐条给出处）
GROUPS = {
    '板条厚度/宽度直接': ['lath thickness', 'lath width', 'block width', 'sub-block',
                          'lath size', 'packet size'],
    '孪晶/层错尺度': ['twin', 'stacking fault', 'twinning', 'martensite twin'],
    '自协调/弹性': ['self-accommodat', 'elastic', 'strain energy', 'invariant plane',
                    'compatibility', 'back stress'],
    '界面能-弹性能竞合': ['interfacial energy', 'surface energy', 'nucleation barrier',
                          'critical thickness', 'driving force'],
    'Ti-64 / LPBF 具体': ['Ti-6Al-4V', 'Ti64', 'LPBF', 'additive manufactur',
                          'alpha prime', 'alpha-prime', "alpha'"],
    '马氏体形核/长大': ['martensite', 'martensitic', 'nucleation', 'growth kinetics',
                        'athermal'],
}
rows = list(csv.DictReader(open(IDX, encoding="utf-8", errors="replace"), delimiter="\t"))
print("索引共 %d 条" % len(rows))


def score(r, kws):
    blob = ' '.join(str(r.get(k, '')) for k in ('file', 'title', 'why')).lower()
    n = sum(1 for k in kws if k in blob)
    rel = 2 if str(r.get('category', '')).upper() == 'REL' else 0
    return n + rel, n


for g, kws in GROUPS.items():
    hits = []
    for r in rows:
        s, n = score(r, [k.lower() for k in kws])
        if n:
            hits.append((s, n, r))
    hits.sort(key=lambda t: (-t[0], -t[1]))
    print("\n" + "=" * 96)
    print("【%s】命中 %d 条（关键词：%s）" % (g, len(hits), ', '.join(kws)))
    print("=" * 96)
    for s, n, r in hits[:10]:
        print("  [%s] %s" % (r.get('category', '?'), str(r.get('file', ''))[:76]))
        t = str(r.get('title', '')).strip()
        if t:
            print("        %s" % t[:104])
