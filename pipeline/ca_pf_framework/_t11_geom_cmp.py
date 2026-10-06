#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_geom_cmp.py <tagA> <tagB> —— 比两臂的**几何跨度**（比 `box_touch` 更本质）。

## 为什么要这个（`R648`）
`R647` 发现：`B40` 与 `B60` 的 `region` **逐位相同**，但 `band_val` 有 **1e-11–1e-8** 的浮点差
⇒ **`box_touch` 这位布尔量会被那点噪声翻转** ⇒ **它不适合作边界判据**。
⇒ 改用**几何量**（三轴跨度占盒比）直接判"是否贴到周期边界"。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tags = sys.argv[1:] or ["B40", "B60"]


def series(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = r.get('box_touch', '?')
            except (KeyError, ValueError):
                pass
    return d


def spanfrac(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        L = float(np.asarray(z['L']).ravel()[0])
        N = int(np.asarray(z['N']).ravel()[0])
    nc, lab = ncomp(reg > 0)
    if lab is None:
        return None
    s = np.bincount(lab.ravel()); s[0] = 0
    m = (lab == int(np.argmax(s)))
    idx = np.argwhere(m)
    sp = (idx.max(0) - idx.min(0) + 1) * (L / N)
    return float(sp.max() / L), int(m.sum())


print("=" * 94)
print("几何跨度占盒比对照：%s" % ' vs '.join(tags))
print("=" * 94)
print("  %-7s %s" % ('step', ' '.join('%-24s' % t for t in tags)))
ser = {t: series(t) for t in tags}
allst = []
for t in tags:
    d = os.path.join(ROOT, "dry_%s" % t)
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.startswith("snap_"):
                with np.load(os.path.join(d, f), allow_pickle=False) as z:
                    allst.append(int(np.asarray(z['step']).ravel()[0]))
common = sorted(set(allst))
for st in common:
    if st % 100 and st not in (475, 500, 525):
        continue
    row = "  %-7d" % st
    for t in tags:
        r = spanfrac(t, st)
        row += " %-24s" % ('—' if r is None else
                           '%.3f (%d胞, bt=%s)' % (r[0], r[1], ser[t].get(st, '?')))
    print(row)
