#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_boxtouch.py <tag> —— 查**撞盒**：引擎的 `box_touch` 列 + 几何自算。

## 为什么必须查
`L1` 跑到 step 1125 时场 2 的 `R1 = 2490 nm`，而盒只有 **4000 nm**（`N=64`×62.5 nm）
⇒ **形状可能已贴到周期边界** ⇒ 之后的长厚比读数**不可作为本征形状**。
本工具：
  · 读引擎 CSV 的 `box_touch` / `box_touch_core` 列（引擎自带判据）；
  · 并用快照**几何自算**：该场主体胞坐标的**任一轴跨度是否 ≥ 0.9·L**。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp  # noqa: E402

tags = sys.argv[1:] or ["L1"]
for tag in tags:
    t = tag[4:] if tag.startswith('dry_') else tag
    p = os.path.join(ROOT, "dry_%s" % t, "series.csv")
    if not os.path.exists(p):
        print("【%s】无 CSV" % t)
        continue
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    print("=" * 92)
    print("【%s】引擎的撞盒列" % t)
    print("=" * 92)
    print("  %-7s %-12s %-14s %s" % ('step', 'box_touch', 'box_touch_core', 'Vt'))
    for r in rows:
        if int(r.get('step', 0)) % 100 and r.get('step') != rows[-1].get('step'):
            continue
        print("  %-7s %-12s %-14s %s"
              % (r.get('step'), r.get('box_touch', '—'),
                 r.get('box_touch_core', '—'), r.get('Vt', '—')))
    # 几何自算
    d = os.path.join(ROOT, "dry_%s" % t)
    sts = []
    for f in sorted(os.listdir(d)):
        if f.startswith("snap_"):
            with np.load(os.path.join(d, f), allow_pickle=False) as z:
                sts.append((int(np.asarray(z['step']).ravel()[0]), f,
                            float(np.asarray(z['L']).ravel()[0]),
                            int(np.asarray(z['N']).ravel()[0])))
    sts.sort()
    print("\n  几何自算（主体胞跨度 / 盒长）：")
    print("  %-7s %-9s %-26s %s" % ('step', '主体胞数', '三轴跨度(nm)', '占比 max'))
    for st, f, L, N in sts[::5] or sts:
        with np.load(os.path.join(d, f), allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
        nc, lab = ncomp(reg > 0)
        if lab is None:
            continue
        s = np.bincount(lab.ravel()); s[0] = 0
        m = (lab == int(np.argmax(s)))
        idx = np.argwhere(m)
        span = (idx.max(0) - idx.min(0) + 1) * (L / N) * 1e9
        print("  %-7d %-9d %-26s %.2f"
              % (st, int(m.sum()), '[%.0f, %.0f, %.0f]' % tuple(span),
                 span.max() / (L * 1e9)))
