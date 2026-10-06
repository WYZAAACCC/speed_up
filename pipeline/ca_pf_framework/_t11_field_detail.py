#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_field_detail.py <tag>@<step> —— **逐场**列出 `(场号, 胞数, Λ)`，判"高 Λ 是不是碎片"。

## 为什么要看胞数
`Λ = R1/R3` 对**细长的小碎片**也会很大（几个胞排成一线 ⇒ `Λ` 很高）
⇒ **不看胞数的 `Λ` 最大值没有意义**。
判据：真正的板条应满足 **胞数大** *且* `Λ` 高；碎片则是 **胞数小** 而 `Λ` 高。
"""
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
for spec in (sys.argv[1:] or ["B40@400"]):
    tag, _, st = spec.partition('@')
    st = int(st)
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        print("缺 %s" % p)
        continue
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
    rows = []
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        n0 = int(m.sum())
        if n0 < 20:
            continue
        nc, lab = ncomp(m)
        if lab is not None and nc > 1:
            s = np.bincount(lab.ravel()); s[0] = 0
            m = (lab == int(np.argmax(s)))
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        rows.append((k, int(m.sum()), n0, met['elong_lt'], met['thick_nm']))
    rows.sort(key=lambda r: -r[1])
    print("=" * 92)
    print("【%s】step %d 逐场明细（按胞数降序）" % (tag, st))
    print("=" * 92)
    print("  %-6s %-9s %-9s %-9s %-9s %s"
          % ('场号', '最大分量胞数', '该场总胞数', 'Λ=R1/R3', '厚(nm)', '判读'))
    tot = sum(r[1] for r in rows)
    for k, nsz, n0, lam, th in rows:
        frac = 100.0 * nsz / max(tot, 1)
        tagp = ('★ 主体' if frac > 20 else
                ('板条' if nsz >= 500 else '碎片(<500胞)'))
        print("  %-6d %-9d %-9d %-9.2f %-9.0f %s（占 %.1f%%）"
              % (k, nsz, n0, lam, th, tagp, frac))
    main = [r for r in rows if r[1] >= 500]
    if main:
        print("\n  ⇒ **只算 ≥500 胞的场**（排除碎片）：%d 个，"
              "`Λ` 中位 = **%.2f**，`Λ` 最大 = **%.2f**"
              % (len(main), float(np.median([r[3] for r in main])),
                 max(r[3] for r in main)))
