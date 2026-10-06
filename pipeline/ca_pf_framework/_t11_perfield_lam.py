#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_perfield_lam.py <tag> —— **逐场**（不是"全场合体"）报长厚比 `Λ`，并标出合并事件。

## 为什么必须改口径（`R643`）
上一版用"**全场最大连通分量**" ⇒ 多片**并排/相连**时被当成一个整体
⇒ `Λ` 被"扁饼"拉低（`L1` 实测：step 350 的 6.12 → step 375 骤降到 4.46，同时胞数 +26%）。
⇒ 正确口径：**逐个场**（每根板条一个 `region` 号）各自算 `Λ`，**报分布**（中位/最大）
   **并报该 step 的场数**，以便识别合并事件。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = (sys.argv[1] if len(sys.argv) > 1 else "L1")
tag = tag[4:] if tag.startswith('dry_') else tag
d = os.path.join(ROOT, "dry_%s" % tag)
p = os.path.join(d, "series.csv")
touch = {}
if os.path.exists(p):
    for r in csv.DictReader(open(p, encoding="utf-8")):
        try:
            touch[int(r['step'])] = int(r.get('box_touch') or 0)
        except (KeyError, ValueError):
            pass

print("=" * 100)
print("【%s】**逐场**长厚比（只用 `box_touch=0`；每场的最大连通分量）" % tag)
print("=" * 100)
print("  %-7s %-9s %-8s %-9s %-9s %-9s %s"
      % ('step', '场数', '胞数', 'Λ 中位', 'Λ 最大', 'Λ 最小', '各场 Λ'))
for f in sorted(os.listdir(d)):
    if not f.startswith("snap_"):
        continue
    with np.load(os.path.join(d, f), allow_pickle=False) as z:
        st = int(np.asarray(z['step']).ravel()[0])
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
    if touch.get(st, 0):
        continue
    lams, cells = [], []
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        if m.sum() < 100:
            continue
        nc, lab = ncomp(m)
        if lab is not None and nc > 1:
            s = np.bincount(lab.ravel()); s[0] = 0
            m = (lab == int(np.argmax(s)))
        if m.sum() < 100:
            continue
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        lams.append((k, met['elong_lt'], int(m.sum())))
    if not lams:
        continue
    v = [x[1] for x in lams]
    print("  %-7d %-9d %-8d %-9.2f %-9.2f %-9.2f %s"
          % (st, len(lams), sum(x[2] for x in lams), float(np.median(v)),
             max(v), min(v),
             ' '.join('%d:%.1f' % (k, l) for k, l, _ in lams[:8])))
