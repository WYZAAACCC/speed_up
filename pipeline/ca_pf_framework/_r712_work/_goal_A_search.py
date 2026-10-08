#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_A_search.py —— A：在**全库**已提取文本里做针对性检索（只读）。

四组检索（D-2 的 `a` 需要的东西）：
  G1 板条几何：Ti-6Al-4V α′ 的 lath width / thickness / length 实测值
  G2 位点/数密度：martensite plate number density / nucleus site density（Ti 系）
  G3 块/packet 尺寸：block / packet size（Ti64 LPBF）
  G4 形核律移植：其他合金上把 a 或 N(T) 标定出来的做法（"怎样在 Ti64 上做"的模板）
"""
import io
import os
import re
import sys

ROOTS = ['/mnt/f/speed_up/_litidx/lit_txt_all']
GROUPS = [
    ('G1-lath几何', r'lath (width|thickness|length|size)|'
                    r'(width|thickness) of (the )?(α.?|alpha.?)?laths?|'
                    r'martensite lath.{0,40}(nm|µm|um)'),
    ('G2-数密度', r'(number|numeric|site) density of (martensite|nucle|plate|α)|'
                  r'nucleation site density|plates? per unit volume|'
                  r'martensite plate density'),
    ('G3-块尺寸', r'block (size|width)|packet (size|width)|'
                  r'prior.?(β|beta) grain size.{0,40}(µm|um|nm)'),
    ('G4-标定模板', r'dN.?dT|nucleus density.{0,40}(measur|determin)|'
                    r'martensite fraction.{0,30}(dilatomet|saturat)|'
                    r'site saturat'),
    ('G5-Ti64形核', r'nucleation.{0,40}(Ti-6Al-4V|Ti6Al4V|titanium)|'
                    r'(Ti-6Al-4V|Ti6Al4V).{0,40}nucleation'),
    ('G6-氧与Ms', r'oxygen.{0,40}(Ms|martensite start)|'
                  r'(Ms|martensite start).{0,40}oxygen'),
]

files = sorted(f for f in os.listdir(ROOTS[0]) if f.endswith('.txt'))
print('扫描 %d 个 txt' % len(files))
hits_by_group = {g: [] for g, _ in GROUPS}
for fn in files:
    L = io.open(os.path.join(ROOTS[0], fn), encoding='utf-8',
                errors='replace').read().splitlines()
    for tag, pat in GROUPS:
        rx = re.compile(pat, re.I)
        for i, s in enumerate(L, 1):
            if rx.search(s):
                hits_by_group[tag].append((fn, i, s.strip()[:170]))

for tag, _ in GROUPS:
    got = hits_by_group[tag]
    print()
    print('=' * 100)
    print('【%s】命中 %d 行，来自 %d 个文件'
          % (tag, len(got), len({g[0] for g in got})))
    print('=' * 100)
    # 优先打印"文件名含 martensite / titanium / Ti"的
    got.sort(key=lambda t: (0 if re.search(r'martens|titani|Ti|α|alpha', t[0], re.I)
                            else 1, t[0]))
    for fn, i, s in got[:22]:
        print('  %-44s :%-5d %s' % (fn[:44], i, s[:118]))
sys.exit(0)
