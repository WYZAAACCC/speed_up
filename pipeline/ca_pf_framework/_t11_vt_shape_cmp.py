#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vt_shape_cmp.py <tagA> <tagB> —— **按 `Vt` 配对**比两臂的形状长厚比。

## 为什么必须按 `Vt` 配对（`P8`）
实测 `L1`（`facet_proj=1`）的生长速度是 `L0`（0）的 **~2.16 倍**
⇒ **同 step 比 = 把"阶段差"当"机制差"**。
⇒ 在**相近 `Vt`** 上比形状，才是同生长阶段的可比对照。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
A, B = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("L0", "L1")


def vt(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = float(r['Vt'])
            except (KeyError, ValueError):
                pass
    return d


def shape(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % (st,))
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
    nc, lab = ncomp(reg > 0)
    if lab is None:
        return None
    s = np.bincount(lab.ravel()); s[0] = 0
    m = (lab == int(np.argmax(s)))
    met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
    return met['elong_lt'], int(m.sum()), len(set(np.unique(reg).tolist()) - {0})


vA, vB = vt(A), vt(B)
print("=" * 96)
print("按 `Vt` 配对比形状：A=%s  vs  B=%s" % (A, B))
print("=" * 96)
print("  %-9s %-12s %-9s %-12s %-8s %s"
      % ('A.step', 'A.Vt', 'B.step', 'B.Vt', 'Vt 差', '长厚比 A -> B'))
rows = []
for sa in sorted(vA):
    if sa % 50:
        continue
    cand = [s for s in sorted(vB)
            if abs(vB[s] - vA[sa]) / max(vA[sa], 1e-300) < 0.30]
    if not cand:
        continue
    sb = min(cand, key=lambda s: abs(vB[s] - vA[sa]))
    ra, rb = shape(A, sa), shape(B, sb)
    if not ra or not rb:
        continue
    e = abs(vB[sb] - vA[sa]) / max(vA[sa], 1e-300)
    rows.append((ra[0], rb[0]))
    print("  %-9d %-12.4g %-9d %-12.4g %-8.1f%% %.2f(%d胞,%d场) -> **%.2f**(%d胞,%d场)"
          % (sa, vA[sa], sb, vB[sb], 100 * e, ra[0], ra[1], ra[2],
             rb[0], rb[1], rb[2]))
if rows:
    ra_ = float(np.median([x[0] for x in rows]))
    rb_ = float(np.median([x[1] for x in rows]))
    print("\n  ⇒ 中位长厚比：A(%s) = **%.2f**  →  B(%s) = **%.2f**  （%d 个配对点）"
          % (A, ra_, B, rb_, len(rows)))
    print("  ⇒ 相对提升 = **%.2f×**" % (rb_ / max(ra_, 1e-9)))
else:
    print("\n  ⚠ 无配对点（`Vt` 无重叠或快照 step 不对齐）")
